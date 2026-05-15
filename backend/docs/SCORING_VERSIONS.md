# Versionado de Scoring y Similaridad

El pipeline RAG ha evolucionado sus medidas de similaridad, puntuacion y filtrado a lo largo de varias versiones. Este documento registra el historico de cada version para facilitar la comparacion y la trazabilidad de decisiones.

## Tabla resumen

| Version | Commits | Pipeline | Busqueda | Fusion | Filtro relevancia | Reranking | Abstencion |
|---------|---------|----------|----------|--------|--------------------|-----------|------------|
| v1 | `86eb6ca` `d65dd68` `9ec5bc6` `846df2e` | vector → contexto → LLM | Coseno (pgvector) | — | — | — | No |
| v2 | `dd0f783` `96548d4` `d768726` | vector + FTS → RRF → filtro → rerank → contexto → LLM | Coseno + ts_rank_cd | RRF (k=60, text_weight=1.5) | score <= 0.35 | Heuristico (4 senales) | Si |
| v3 | `da66796` | = v2 + pre-filtro lexico | = v2 | = v2 | = v2 | = v2 + pre-filtro lexico | Si |
| v4 | `6d441e6` | = v3 (RAG sin cambios); search usa config separada | = v3 (RAG); search `retrieval_k=200` | = v3 | RAG 0.35; search 0.55 | RAG = v3; search: base 0.6, title 0.2, coverage 0.15, position 0.05 | Si |
| v5 | pendiente | RAG: modo similarity-only configurable (`RAG_SIMILARITY_ONLY`) | Coseno puro (cuando activado) | — (bypass) | score <= 0.25 (`RAG_SIMILARITY_THRESHOLD`) | — (bypass) | Si |
| v6 | pendiente | + instruccion Qwen3 en queries + recalibracion thresholds | = v5 | = v5 | similarity 0.45; RAG hibrido 0.50 | = v5 | Si |
| v7 | pendiente | + reranking neuronal opcional (Qwen3-Reranker-0.6B) | = v6 | = v6 | = v6 | Neural cross-encoder (cuando `RERANKER_ENABLED=true`); heuristico como fallback | Si |

## Versiones

### v1 — Solo busqueda vectorial (2026-03-11)

- **Commits**:
  - `86eb6ca` — _feat: add domain layer with entities, ports and services for all bounded contexts_
  - `d65dd68` — _feat: add application layer with DTOs, use cases and services for all bounded contexts_
  - `9ec5bc6` — _feat: add infrastructure adapters, ORM models, repositories and composition root_
  - `846df2e` — _chore: remap service ports to 1xxxx range and tune vLLM memory settings_ (`llm_max_tokens` 2048 → 512)
- **Pipeline**: embed → busqueda vectorial → ensamblado de contexto → generacion LLM

| Componente | Detalle |
|---|---|
| Busqueda | Coseno (`<=>` pgvector), indice HNSW `vector_cosine_ops`, dim=768 |
| `rag_top_k` | 5 (unico parametro — controlaba busqueda y contexto) |
| `llm_temperature` | 0.7 |
| `llm_max_tokens` | 2048 → 512 (`846df2e`, 2026-03-12) |
| Contexto LLM | Sin limite de caracteres |
| Filtrado | Ninguno |
| Reranking | Ninguno |
| Abstencion | No — si no habia resultados relevantes, el LLM alucinaba |

### v2 — Busqueda hibrida + RRF + reranking heuristico (2026-03-13)

- **Commits**:
  - `dd0f783` — _feat: add hybrid search with RRF, heuristic re-ranking, relevance filtering and abstention_
  - `96548d4` — _fix: prevent LLM context overflow with char budget and 400-error retry_ (`max_context_chars=6000`)
  - `d768726` — _fix: improve RAG response quality with listing prompt, retry embeddings and docs restructure_ (`rag_top_k` 3 → 5)

**Cambios respecto a v1**:

1. **Busqueda full-text** anadida (tsvector con `ts_rank_cd`, stemmer espanol)
2. **Fusion hibrida** via Reciprocal Rank Fusion
3. **Filtro de relevancia** por umbral de distancia coseno
4. **Reranking heuristico** con 4 senales ponderadas
5. **Abstencion** cuando ningun chunk pasa el filtro

#### Parametros

| Parametro | Valor | Cambio vs v1 |
|---|---|---|
| `rag_retrieval_k` | 20 | Nuevo — chunks recuperados por cada busqueda |
| `rag_top_k` | 3 → 5 | Reducido inicialmente a 3 con reranking, restaurado a 5 en `d768726` |
| `rag_score_threshold` | 0.35 | Nuevo — umbral de filtro de relevancia |
| `llm_temperature` | 0.3 | Reducida desde 0.7 para mayor precision |
| `llm_max_tokens` | 512 | Sin cambio |
| `max_context_chars` | 6000 | Nuevo — anadido en `96548d4` para evitar overflow |

#### Busqueda vectorial (sin cambios)

- Metrica: distancia coseno (`<=>` pgvector)
- Rango: 0 (identico) – 1 (tipico)
- Orden: ascendente (menor = mas relevante)

#### Busqueda full-text

- Funcion de ranking: `ts_rank_cd()` (Cover Density Rank)
- Stemmer: espanol (`plainto_tsquery('spanish', ...)`)
- Rango: 0 a ∞ (sin acotar)
- Orden: descendente (mayor = mas relevante)
- Preprocesamiento: eliminacion de stopwords y tokens cortos

#### Fusion hibrida — Reciprocal Rank Fusion (`HybridSearchService`)

| Parametro | Valor |
|---|---|
| `k_param` | 60 |
| `text_weight` | 1.5 |

Formula:
- Vector: `rrf_score += 1.0 / (60 + rank + 1)`
- Texto:  `rrf_score += 1.5 / (60 + rank + 1)`
- Chunks en ambas listas reciben bonus acumulado

Normalizacion de salida:
```
relevance = rrf_score / max_rrf
normalized_score = 1.0 - relevance    # escala distancia (0 = mejor)
```

#### Filtro de relevancia (`RelevanceFilterService`)

- Criterio: `chunk.score <= 0.35`
- Si ningun chunk pasa → respuesta de abstencion

#### Reranking heuristico (`RerankingService`)

| Senal | Peso | Calculo |
|---|---|---|
| `base` | 0.4 | `1.0 - cosine_distance` |
| `title` | 0.3 | Fraccion de terminos query en titulo |
| `coverage` | 0.2 | Fraccion de terminos query en contenido |
| `position` | 0.1 | Fijo `0.5` (neutral; `chunk_index` no disponible) |

Formula: `score = 0.4 × base + 0.3 × title + 0.2 × coverage + 0.1 × position`

Normalizacion: `1.0 - (score / max_score)` → escala distancia (0 = mejor)

Tokenizacion: regex `\w+`, lowercase, filtro de stopwords espanolas + terminos conversacionales (`dame`, `hablame`, `dime`, `informacion`).

#### Ensamblado de contexto (`ContextAssemblyService`)

- Formato: `[idx] titulo (tipo, provincia)\ncontenido\nFuente: url`
- Presupuesto: 6000 caracteres maximo; deja de anadir chunks al excederlo

### v3 — Pre-filtro lexico en reranking (2026-03-16)

- **Commits**:
  - `da66796` — _feat: add municipality/metadata to RAG sources and lexical pre-filter to reranking_

**Cambios respecto a v2**:

1. **Pre-filtro lexico** anadido al `RerankingService`: antes de puntuar, descarta chunks con **cero coincidencia lexica** (ningun termino de la query aparece en titulo ni contenido)
2. Si todos los chunks son descartados por el pre-filtro → respuesta de abstencion
3. Logging detallado de scores con desglose por componente (`base`, `title`, `coverage`, `position`)

Todos los demas parametros y formulas permanecen identicos a v2.

### v4 — Config separada para search con reranking dominado por embedding (2026-03-19, actual)

- **Commits**:
  - `6d441e6` — _feat: add search-specific retrieval config and embedding-dominant reranking weights_

**Cambios respecto a v3**:

1. **Separacion de config RAG vs Search**: el contexto `search` deja de compartir `rag_retrieval_k` y `rag_score_threshold`, y usa sus propios parametros en `config.py`
2. **Mayor volumen de recuperacion**: `search_retrieval_k=200` (vs `rag_retrieval_k=20`) — la busqueda facetada necesita un pool mucho mayor para agrupar por asset
3. **Umbral de relevancia mas estricto**: `search_score_threshold=0.55` (vs `rag_score_threshold=0.35`) — filtra con mayor agresividad porque el volumen de candidatos es mayor
4. **Reranking dominado por embedding**: se redistribuyen los pesos para priorizar la senal vectorial sobre las senales lexicas

#### Pesos de reranking por contexto

| Senal | RAG (sin cambio) | Search (nuevo) |
|---|---|---|
| `weight_base` | 0.4 | 0.6 |
| `weight_title` | 0.3 | 0.2 |
| `weight_coverage` | 0.2 | 0.15 |
| `weight_position` | 0.1 | 0.05 |

**Justificacion**: en el contexto de busqueda facetada, las queries suelen ser cortas y genericas (ej. "iglesias de Sevilla"). La senal de embedding captura mejor la semantica que las coincidencias lexicas parciales. Se reduce el peso de `title` y `coverage` para evitar que terminos comunes dominen el ranking.

#### Cableado (`search_composition.py`)

Los parametros se inyectan explicitamente en la composicion del contexto `search`:
- `RelevanceFilterService(score_threshold=settings.search_score_threshold)`
- `RerankingService(weight_base=0.6, weight_title=0.2, weight_coverage=0.15, weight_position=0.05)`
- `retrieval_k=settings.search_retrieval_k`

El pipeline RAG (`rag_composition.py`) no se modifica — sigue usando los parametros `rag_*` originales.

## Evolucion de parametros

| Parametro | v1 (2026-03-11) | v2 (2026-03-13) | v3 (2026-03-16) | v4 (2026-03-19) | v6 (2026-03-26) | v7 (2026-03-27) |
|---|---|---|---|---|---|---|
| `rag_top_k` | 5 | 3 → 5 | 5 | 5 | 5 | 5 |
| `rag_retrieval_k` | — | 20 | 20 | 20 | 20 | 20 |
| `search_retrieval_k` | — | — | — | 200 | 200 | 200 |
| `rag_score_threshold` | — | 0.35 | 0.35 | 0.35 | **0.50** | 0.50 |
| `rag_similarity_threshold` | — | — | — | — | **0.45** | 0.45 |
| `search_score_threshold` | — | — | — | 0.55 | 0.55 | 0.55 |
| `embedding_query_instruction` | — | — | — | — | **Retrieve...** | = v6 |
| `reranker_enabled` | — | — | — | — | — | **false** (toggle) |
| `reranker_top_n` | — | — | — | — | — | **50** |
| `llm_temperature` | 0.7 | 0.3 | 0.3 | 0.3 | 0.3 | 0.3 |
| `llm_max_tokens` | 2048 → 512 | 512 | 512 | 512 | 512 | 512 |
| `max_context_chars` | ∞ | 6000 | 6000 | 6000 | 6000 | 6000 |
| RRF `k_param` | — | 60 | 60 | 60 | 60 | 60 |
| RRF `text_weight` | — | 1.5 | 1.5 | 1.5 | 1.5 | 1.5 |
| Reranking | — | Heuristico | + pre-filtro | Config separada | bypass (sim-only) | **Neural cross-encoder** |
| Pre-filtro lexico | — | — | Chunks con 0 match descartados | = v3 | = v3 | — (reemplazado por neural) |
| Abstencion | No | Si | Si | Si | Si | Si |

### v5 — Modo similarity-only configurable (2026-03-25, actual)

- **Commits**: pendiente

**Cambios respecto a v4**:

1. **Nuevo flag `RAG_SIMILARITY_ONLY`** (default `false`): cuando se activa, el pipeline RAG salta text search, fusion RRF y reranking heuristico
2. **Pipeline simplificado**: `embed → vector search (coseno) → filtro relevancia → top-k → contexto → LLM`
3. **Retrocompatible**: con `RAG_SIMILARITY_ONLY=false` el pipeline es identico a v4

#### Pipeline con `RAG_SIMILARITY_ONLY=true`

| Componente | Detalle |
|---|---|
| Busqueda | Solo coseno (`<=>` pgvector) |
| Fusion | — (bypass) |
| Filtro relevancia | `score <= RAG_SIMILARITY_THRESHOLD` (default 0.25) — threshold separado calibrado para distancia coseno cruda |
| Reranking | — (bypass) |
| Ordenacion | Por cosine distance ascendente → top_k |
| Logging | Scores individuales por chunk (titulo, tipo, provincia) |
| Abstencion | Si — si ningun chunk pasa el umbral |

**Nota sobre escala de scores**: en modo hibrido, los scores estan normalizados a 0-1 via RRF. En similarity-only, los scores son distancia coseno cruda de pgvector (rango 0-2, donde 0=identico). Por eso se usa un threshold separado (`RAG_SIMILARITY_THRESHOLD=0.25`) en lugar de `RAG_SCORE_THRESHOLD=0.35` o `SEARCH_SCORE_THRESHOLD=0.55`, que estan calibrados para la escala RRF.

#### Parametros nuevos

| Parametro | Valor | Descripcion |
|---|---|---|
| `RAG_SIMILARITY_ONLY` | `false` | `true` = similaridad pura, `false` = pipeline hibrido completo |
| `RAG_SIMILARITY_THRESHOLD` | `0.25` | Umbral de distancia coseno para similarity-only (escala pgvector 0-2) |

El flag aplica a **todos los contextos**: RAG (chat), search (busqueda facetada) y routes (via RAG). Un solo flag controla los tres.

### v6 — Instruccion Qwen3 para queries + recalibracion de thresholds (2026-03-26)

- **Commits**: pendiente

**Cambios respecto a v5**:

1. **Prefijo de instruccion para queries**: las queries se envuelven con `Instruct: {instruction}\nQuery: {query}` antes de embedirlas. Los documentos NO llevan instruccion (asimetria query/document requerida por Qwen3).
2. **Recalibracion de thresholds** basada en benchmark con 8 queries y ground truth manual.
3. **Nueva variable de entorno `EMBEDDING_QUERY_INSTRUCTION`**: configurable, se desactiva con cadena vacia (para MrBERT u otros modelos simetricos).

#### Causa raiz diagnosticada

Qwen3-Embedding-0.6B es un modelo **instruction-aware** con arquitectura decoder-only. Sin el prefijo de instruccion, las queries caen en la "region de documentos" del espacio de embeddings, produciendo distancias coseno 17-60% mas altas que con instruccion. Ver `QWEN3_EMBEDDING_DIAGNOSTICO.md` para el analisis completo.

#### Resultados del benchmark

| Query | Sin instruccion (v5) | Con instruccion (v6) | Mejora | Resultado #1 |
|-------|---------------------|---------------------|--------|-------------|
| cuevas del sacromonte | 0.4261 (filtrado) | 0.3557 | **-17%** | Sector Valparaiso-Sacromonte |
| alhambra granada | 0.3722 (filtrado) | 0.2456 | **-34%** | Vista de la Alhambra de Granada |
| mezquita cordoba | 0.4991 (filtrado) | 0.1987 | **-60%** | Mezquita Catedral |

MRR global: 0.442 (v5) → **0.875** (v6)

#### Parametros modificados

| Parametro | v5 | v6 | Motivo |
|---|---|---|---|
| `EMBEDDING_QUERY_INSTRUCTION` | — | `Retrieve relevant heritage documents.` | Nuevo — activa prefijo Qwen3 |
| `RAG_SIMILARITY_THRESHOLD` | 0.25 | **0.45** | Recalibrado para Qwen3 con instrucciones |
| `RAG_SCORE_THRESHOLD` | 0.35 | **0.50** | Recalibrado para modo hibrido con Qwen3 |

#### Implementacion

- Helper: `domain/rag/services/query_instruction_service.py` — `wrap_query_for_embedding(query, instruction)`
- Aplicado en `RAGQueryUseCase.execute()` y `SimilaritySearchUseCase.execute()` antes de llamar a `embed()`
- Retrocompatible: `EMBEDDING_QUERY_INSTRUCTION=` (vacio) desactiva el prefijo

### v7 — Reranking neuronal con Qwen3-Reranker-0.6B (2026-03-27)

- **Commits**: pendiente

**Cambios respecto a v6**:

1. **Reranking neuronal** opcional via cross-encoder (`Qwen3-Reranker-0.6B`, 0.6B params, 32k contexto)
2. **Co-localizado** con el servicio de embeddings (`embedding/main.py`, endpoint `POST /rerank`)
3. **Retrocompatible**: `RERANKER_ENABLED=false` (default) preserva el comportamiento de v6 exactamente
4. **Activacion en modo similarity-only**: cuando `RERANKER_ENABLED=true` y `RAG_SIMILARITY_ONLY=true`, el pipeline aplica reranking neuronal despues del filtro de similaridad (antes este path saltaba el reranking)

#### Modelo: Qwen3-Reranker-0.6B

| Propiedad | Valor |
|---|---|
| Parametros | 600M |
| Contexto maximo | 32,768 tokens |
| Arquitectura | Causal LM (decoder-only) |
| Scoring | P(yes) via softmax sobre logits "yes"/"no" |
| Input | `<Instruct>: {instruction}\n<Query>: {query}\n<Document>: {document}` |

#### Pipeline con `RERANKER_ENABLED=true`

El reranker neuronal reemplaza al heuristico en la misma posicion del pipeline:

| Modo | Pipeline |
|---|---|
| `RAG_SIMILARITY_ONLY=true` (recomendado) | vector → filtro similaridad → **neural rerank** → top-k → contexto → LLM |
| `RAG_SIMILARITY_ONLY=false` | vector + FTS → RRF → filtro relevancia → **neural rerank** → top-k → contexto → LLM |

#### Scoring del cross-encoder

1. Formatea cada par query-documento con el template de chat del modelo (system/user/assistant)
2. Anade tokens de pensamiento: `<think>\n\n</think>\n\n`
3. Forward pass → extrae logits en la ultima posicion para tokens "yes"/"no"
4. `score = softmax([yes_logit, no_logit])[0]` → probabilidad de relevancia (0-1)
5. Convierte a escala de distancia: `distance = 1.0 - relevance` (0 = mas relevante)

#### Parametros nuevos

| Parametro | Valor por defecto | Descripcion |
|---|---|---|
| `RERANKER_ENABLED` | `false` | Activa reranking neuronal |
| `RERANKER_SERVICE_URL` | `http://localhost:18001` | URL del servicio (misma que embedding) |
| `RERANKER_INSTRUCTION` | `Given a heritage search query, retrieve relevant heritage documents.` | Instruccion para el cross-encoder |
| `RERANKER_TOP_N` | `50` | Maximo de candidatos enviados al reranker (control de latencia) |

#### Matriz de configuracion recomendada

| Modo | `RAG_SIMILARITY_ONLY` | `RERANKER_ENABLED` | Pipeline |
|------|----------------------|-------------------|----------|
| v6 (actual) | `true` | `false` | vector → filtro → top-k |
| **v7 (recomendado)** | `true` | `true` | vector → filtro → neural rerank → top-k |
| v7 hibrido | `false` | `true` | vector + FTS → RRF → filtro → neural rerank → top-k |
| v4 legacy | `false` | `false` | vector + FTS → RRF → filtro → heuristico → top-k |

#### Implementacion

- Co-localizado en `embedding/main.py` — endpoint `POST /rerank` junto a `POST /embed`
- El modelo se carga al arrancar si existe en `RERANKER_MODEL_PATH` (volumen Docker)
- Puerto: RerankerPort (`domain/rag/ports/reranker_port.py`)
- Adaptador: HttpRerankerAdapter (`infrastructure/rag/adapters/reranker_adapter.py`)
- Servicio: NeuralRerankingService (`domain/rag/services/neural_reranking_service.py`)
- Composicion: wiring condicional en `rag_composition.py` y `search_composition.py`
- Docker: mismo contenedor que embedding, modelo montado en `/app/reranker_model` (path parametrizado via `RERANKER_MODEL_DIR`, default `Qwen3-Reranker-0.6B`)

#### Auto-deteccion de arquitectura (2026-05-15)

Desde el commit `2e488a4`, `embedding/main.py` detecta la arquitectura del reranker leyendo `architectures` de `config.json` al arrancar y elige la ruta de scoring adecuada. Esto permite servir tanto el `Qwen3-Reranker-0.6B` original como el nuevo `SINAI/ALIA-MrBERT-es-cultural-reranker` (entregado por UJA/SINAI el 2026-05-11) desde el mismo servicio sin cambios de codigo.

| Familia (config.json) | Variable interna | Pre-procesado de input | Funcion de score |
|---|---|---|---|
| `*ForCausalLM` (Qwen3-Reranker) | `reranker_type="causal"` | `<Instruct>: ...\n<Query>: ...\n<Document>: ...` + chat template + tokens de pensamiento | `softmax([logit_yes, logit_no])[0]` |
| `*ForSequenceClassification` (SINAI cultural, ModernBERT, num_labels=1) | `reranker_type="seq_class"` | Pair plain text `(query, doc)` → `[CLS] query [SEP] doc [SEP]` — `RERANKER_INSTRUCTION` se ignora | `sigmoid(logit)` (o `softmax(logits)[:, 1]` si `num_labels==2`) |

El campo `reranker_type` se publica en `GET /health` para verificacion. Funcion `_score_pairs_causal` y `_score_pairs_seq_class` en `embedding/main.py`.

#### Reranker SINAI cultural

| Propiedad | Valor |
|---|---|
| Base | MrBERT-es (ModernBERT, ~150M params) |
| Loss de entrenamiento | `BinaryCrossEntropyLoss` (CrossEncoder de `sentence-transformers`) |
| Head | `num_labels=1` |
| Activacion | sigmoid |
| Max seq | 8,192 tokens |
| Licencia | Apache-2.0 |
| Cloud Run | Activo en `uja-embedding-00012-wv2` con `RERANKER_BATCH_SIZE=8` |

## Como anadir una nueva version

1. Implementar los cambios en los servicios de `domain/rag/services/`, `config.py` o `composition/<context>_composition.py`
2. Documentar la nueva version en este fichero con los parametros y formulas
3. Registrar el commit y la fecha
