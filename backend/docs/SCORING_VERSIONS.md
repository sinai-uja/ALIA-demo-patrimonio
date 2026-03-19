# Versionado de Scoring y Similaridad

El pipeline RAG ha evolucionado sus medidas de similaridad, puntuacion y filtrado a lo largo de varias versiones. Este documento registra el historico de cada version para facilitar la comparacion y la trazabilidad de decisiones.

## Tabla resumen

| Version | Commits | Pipeline | Busqueda | Fusion | Filtro relevancia | Reranking | Abstencion |
|---------|---------|----------|----------|--------|--------------------|-----------|------------|
| v1 | `86eb6ca` `d65dd68` `9ec5bc6` `846df2e` | vector → contexto → LLM | Coseno (pgvector) | — | — | — | No |
| v2 | `dd0f783` `96548d4` `d768726` | vector + FTS → RRF → filtro → rerank → contexto → LLM | Coseno + ts_rank_cd | RRF (k=60, text_weight=1.5) | score <= 0.35 | Heuristico (4 senales) | Si |
| v3 | `da66796` | = v2 + pre-filtro lexico | = v2 | = v2 | = v2 | = v2 + pre-filtro lexico | Si |

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

### v3 — Pre-filtro lexico en reranking (2026-03-16, actual)

- **Commits**:
  - `da66796` — _feat: add municipality/metadata to RAG sources and lexical pre-filter to reranking_

**Cambios respecto a v2**:

1. **Pre-filtro lexico** anadido al `RerankingService`: antes de puntuar, descarta chunks con **cero coincidencia lexica** (ningun termino de la query aparece en titulo ni contenido)
2. Si todos los chunks son descartados por el pre-filtro → respuesta de abstencion
3. Logging detallado de scores con desglose por componente (`base`, `title`, `coverage`, `position`)

Todos los demas parametros y formulas permanecen identicos a v2.

## Evolucion de parametros

| Parametro | v1 (2026-03-11) | v2 (2026-03-13) | v3 (2026-03-16) |
|---|---|---|---|
| `rag_top_k` | 5 | 3 → 5 | 5 |
| `rag_retrieval_k` | — | 20 | 20 |
| `rag_score_threshold` | — | 0.35 | 0.35 |
| `llm_temperature` | 0.7 | 0.3 | 0.3 |
| `llm_max_tokens` | 2048 → 512 | 512 | 512 |
| `max_context_chars` | ∞ | 6000 | 6000 |
| RRF `k_param` | — | 60 | 60 |
| RRF `text_weight` | — | 1.5 | 1.5 |
| Rerank `weight_base` | — | 0.4 | 0.4 |
| Rerank `weight_title` | — | 0.3 | 0.3 |
| Rerank `weight_coverage` | — | 0.2 | 0.2 |
| Rerank `weight_position` | — | 0.1 | 0.1 |
| Pre-filtro lexico | — | — | Chunks con 0 match descartados |
| Abstencion | No | Si | Si |

## Como anadir una nueva version

1. Implementar los cambios en los servicios de `domain/rag/services/` o `config.py`
2. Documentar la nueva version en este fichero con los parametros y formulas
3. Registrar el commit y la fecha
