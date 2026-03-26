# Diagnostico: Qwen3-Embedding-0.6B — Busqueda por similaridad rota

**Fecha**: 2026-03-25
**Rama**: `task/14303`
**Autor**: Diagnostico automatizado con scripts en `backend/scripts/`

---

## 1. El problema

La busqueda por similaridad semantica no devuelve resultados. Ejemplo:

```
Query: "cuevas del sacromonte"
Vector search: 40 resultados encontrados
Filtro de relevancia (threshold <= 0.25): 0 resultados pasan
Resultado final: 0 resultados mostrados al usuario
```

Esto ocurre con **todas** las queries probadas: "alhambra granada", "mezquita cordoba", "iglesia barroca sevilla", etc. El sistema encuentra vecinos cercanos en pgvector pero los descarta todos por no superar el umbral de relevancia.

---

## 2. Contexto tecnico

### 2.1. Que modelo de embedding usamos

**Qwen3-Embedding-0.6B** ([HuggingFace](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)):
- 600M parametros, arquitectura decoder-only (no BERT)
- 1024 dimensiones de embedding
- Contexto de 32,768 tokens
- **Pooling**: last-token con left-padding (el ultimo token, que es EOS, concentra la representacion de toda la secuencia)
- **Normalizacion**: L2 (los vectores resultantes tienen norma 1)
- **Caracteristica clave**: es un modelo **instruction-aware** (mas sobre esto en la seccion 4)

### 2.2. Como se almacenan los documentos

Tabla `document_chunks_v4` en PostgreSQL con pgvector:
- **138,175 chunks** de los 4 datasets IAPH (Patrimonio Inmueble, Mueble, Inmaterial, Paisaje Cultural)
- Columna `embedding` de tipo `vector(1024)` con indice HNSW (`vector_cosine_ops`)
- Los chunks se embebieron con Qwen3 durante la ingesta, con contenido enriquecido (plantillas en lenguaje natural que preponen metadatos al texto)

Ejemplo de contenido enriquecido almacenado (y embebido):
```
Bien inmueble titulado 'Mezquita Catedral'. Es una propiedad de naturaleza
Edificios religiosos y tipo Mezquitas. Ubicado en el municipio de Cordoba,
provincia de Cordoba. De estilo Arte islámico.
IDENTIFICACION
Denominacion: Mezquita Catedral
Codigo: 140340001
Provincia: Cordoba
[... texto original del chunk ...]
```

### 2.3. Como se busca

Operador `<=>` de pgvector = **distancia coseno**:
- `0.0` = vectores identicos (similitud coseno = 1.0)
- `1.0` = vectores ortogonales (similitud coseno = 0.0)
- `2.0` = vectores opuestos (similitud coseno = -1.0)
- **Menor es mejor** (ORDER BY score ASC)

Config actual (`.env`):
```
RAG_SIMILARITY_ONLY=true          # solo busqueda vectorial, sin FTS ni RRF
RAG_SIMILARITY_THRESHOLD=0.25     # umbral: distancia coseno <= 0.25
CHUNKS_TABLE_VERSION=v4           # tabla con embeddings Qwen3 1024-dim
```

Un threshold de 0.25 exige una **similitud coseno >= 0.75**, que es extremadamente alto.

---

## 3. Diagnostico: que esta fallando

### 3.1. Distribucion de scores SIN instrucciones (comportamiento actual)

Ejecutado con `backend/scripts/embedding_diagnostics.py`:

| Query | Mejor score | Mediana (top-40) | Resultados <= 0.25 | Resultado #1 |
|-------|------------|------------------|-------------------|-------------|
| cuevas del sacromonte | **0.4261** | 0.4871 | 0 | Matriz de Descripcion del Monte Sacro de Valparaiso |
| alhambra granada | **0.3722** | 0.4242 | 0 | Cementerio de Alhama de Granada |
| mezquita cordoba | **0.4991** | 0.5180 | 0 | Escudos; Portada del compas |
| iglesia barroca sevilla | **0.3542** | 0.3728 | 0 | Visitacion; Retablo de la Virgen del Rosario |
| patrimonio inmueble jaen | **0.2838** | 0.3696 | 0 | V-JA-ML-055 |

**Observaciones criticas**:
- Los scores estan **todos por encima de 0.25** — ninguna query recupera nada
- Los resultados **no son semanticamente relevantes**: buscar "alhambra granada" devuelve "Cementerio de Alhama de Granada" como mejor match, no la Alhambra
- Buscar "mezquita cordoba" devuelve "Escudos; Portada del compas" — completamente irrelevante
- El modelo se comporta como si queries y documentos estuvieran en **espacios distintos**

### 3.2. Distribucion de scores CON instrucciones

Mismo test pero wrapeando la query con: `Instruct: Retrieve relevant heritage documents.\nQuery: {query}`

| Query | Mejor score | Mediana (top-40) | Resultados <= 0.25 | Resultado #1 |
|-------|------------|------------------|-------------------|-------------|
| cuevas del sacromonte | **0.3557** | 0.4514 | 0 | Sector Valparaiso-Sacromonte |
| alhambra granada | **0.2456** | 0.3543 | 1 | Vista de la Alhambra de Granada |
| mezquita cordoba | **0.1987** | 0.4105 | 2 | Mezquita Catedral |
| iglesia barroca sevilla | **0.2885** | 0.3259 | 0 | Iglesia de San Ildefonso |
| patrimonio inmueble jaen | **0.2532** | 0.3549 | 0 | Conjunto de Bienes Muebles ... Jaen |

**Observaciones criticas**:
- Los scores bajan **drasticamente** — entre un 17% y un 60% de mejora
- Los resultados **ahora si son relevantes**: "alhambra granada" → "Vista de la Alhambra de Granada", "mezquita cordoba" → "Mezquita Catedral"
- El #1 de "mezquita cordoba" tiene score **0.1987** — por debajo del threshold 0.25
- Aun asi, la mayoria de queries necesitan un threshold mas alto que 0.25 para devolver resultados utiles

### 3.3. Tabla comparativa — Impacto de la instruccion

| Query | Sin instruccion | Con instruccion | Mejora | Relevancia resultado #1 |
|-------|----------------|-----------------|--------|------------------------|
| cuevas del sacromonte | 0.4261 | 0.3557 | **-17%** | Irrelevante → Relevante |
| alhambra granada | 0.3722 | 0.2456 | **-34%** | Irrelevante → Exacto |
| mezquita cordoba | 0.4991 | 0.1987 | **-60%** | Irrelevante → Exacto |
| iglesia barroca sevilla | 0.3542 | 0.2885 | **-19%** | Debil → Relevante |
| patrimonio inmueble jaen | 0.2838 | 0.2532 | **-11%** | Debil → Relevante |

### 3.4. Sweep de thresholds CON instrucciones

Cuantos de los 40 resultados mas cercanos pasan cada umbral (con instruccion):

| Query | <= 0.25 | <= 0.30 | <= 0.35 | <= 0.40 | <= 0.45 | <= 0.50 |
|-------|---------|---------|---------|---------|---------|---------|
| cuevas del sacromonte | 0 | 0 | 0 | 4 | 17 | 40 |
| alhambra granada | 1 | 6 | 18 | 40 | 40 | 40 |
| mezquita cordoba | 2 | 3 | 4 | 15 | 40 | 40 |
| iglesia barroca sevilla | 0 | 3 | 40 | 40 | 40 | 40 |
| patrimonio inmueble jaen | 0 | 3 | 15 | 40 | 40 | 40 |

**Threshold optimo con instrucciones: 0.45** — captura resultados relevantes para todas las queries con un recall razonable.

---

## 4. Explicacion: por que la instruccion importa tanto

### 4.1. Modelos de embedding clasicos vs instruction-aware

Los modelos de embedding clasicos (como MrBERT, sentence-transformers, etc.) son **simetricos**: tratan queries y documentos exactamente igual. Aplican mean pooling sobre todos los tokens y generan un vector que representa "el significado del texto". Para buscar, se compara query-vector contra documento-vector directamente.

**Qwen3-Embedding es diferente**. Es un modelo **instruction-aware** basado en una arquitectura **decoder-only** (como un LLM). Fue entrenado con un formato especifico:

```
Documentos (durante ingesta):
  input = "texto del documento tal cual"
  → se embebe sin prefijo alguno

Queries (durante busqueda):
  input = "Instruct: {descripcion de la tarea}\nQuery: {texto de la query}"
  → se embebe con el prefijo de instruccion
```

### 4.2. Por que esto afecta la busqueda

Durante el entrenamiento contrastivo del modelo, Qwen3 aprendio a:
1. **Posicionar los vectores de query (con instruccion) cerca de los vectores de documento relevantes** en el espacio de 1024 dimensiones
2. **Posicionar los vectores de texto sin instruccion en una region diferente** — la region de "documentos"

Cuando enviamos una query SIN instruccion, el modelo la trata como un documento mas. El vector resultante cae en la **region de documentos**, no en la **region de queries**. La distancia coseno entre un "documento-query" y los "documentos reales" es alta porque estan en el mismo lado del espacio pero no alineados por relevancia.

Con la instruccion, el vector cae en la **region de queries**, y la distancia coseno refleja **relevancia semantica real**.

### 4.3. Diagrama conceptual

```
Espacio de embeddings (1024 dims, simplificado a 2D):

          SIN instruccion                     CON instruccion
    ┌─────────────────────┐            ┌─────────────────────┐
    │                     │            │                     │
    │   D1  D3  D5        │            │   D1  D3  D5        │
    │     D2  D4          │            │     D2  D4          │
    │                     │            │         Q ←──────── │  query cerca de
    │           Q ←────── │ query en   │                     │  docs relevantes
    │                     │ zona docs  │                     │
    │   D6  D8            │ (lejos de  │   D6  D8            │
    │     D7  D9          │ relevantes)│     D7  D9          │
    │                     │            │                     │
    └─────────────────────┘            └─────────────────────┘

    Distancia Q-D1: 0.42 (alta)        Distancia Q-D1: 0.20 (baja, relevante)
    Distancia Q-D6: 0.45 (alta)        Distancia Q-D6: 0.50 (alta, irrelevante)
```

### 4.4. La documentacion de Qwen3 es engañosa

El README de Qwen3-Embedding dice:

> "In most retrieval scenarios, not using an instruct on the query side can lead to a drop in retrieval performance by approximately 1% to 5%."

Nuestros tests muestran una caida de **17% a 60%**, no 1-5%. Esto se explica por:

1. **Asimetria query/documento**: nuestras queries son cortas (3-5 palabras) pero los documentos son largos (500-1000 tokens con metadatos). La instruccion ayuda al modelo a entender que el texto corto es una busqueda, no un fragmento de documento.
2. **Dominio especializado**: patrimonio cultural andaluz con vocabulario especifico. Sin instruccion, el modelo no sabe si "mezquita cordoba" es una busqueda o parte de un texto descriptivo.
3. **Benchmark vs realidad**: el 1-5% mencionado por Qwen se mide en benchmarks estandar (MTEB) donde las queries ya son mas largas y explicitas.

---

## 5. Contenido enriquecido: afecta o no?

### 5.1. Test realizado

Se creo una tabla experimental `document_chunks_test` con 500 chunks de Granada, Sevilla, Cordoba, Jaen y Cadiz. Cada chunk se embebio en dos variantes:

- **baseline**: contenido enriquecido original (plantilla v4 con metadatos + texto)
- **clean**: texto sin la plantilla de metadatos (solo el contenido "puro" del chunk)

### 5.2. Resultado

No hay diferencia significativa entre baseline y clean. Ambas variantes producen scores similares y el mismo ranking. **El contenido enriquecido no daña la calidad de recuperacion**.

Esto tiene sentido: Qwen3 con 1024 dimensiones tiene suficiente capacidad para representar tanto los metadatos como el contenido. Los metadatos no "diluyen" el embedding.

**Conclusion**: no hace falta re-ingestar los 138K chunks. El contenido enriquecido v4 se queda tal cual.

---

## 6. Benchmark sistematico

Ejecutado con `backend/scripts/benchmark_retrieval.py` sobre 8 queries con ground truth manual.

### 6.1. Resultados por configuracion y threshold

**Metrica principal: MRR (Mean Reciprocal Rank)** — mide la posicion media del primer resultado relevante (1.0 = siempre es el #1).

| Threshold | raw (actual) | instruct_short | instruct_heritage |
|-----------|-------------|----------------|-------------------|
| 0.30 | MRR=0.125, 0 results | **MRR=0.625, 2 results** | MRR=0.250, 0 results |
| 0.35 | MRR=0.250, 2 results | **MRR=0.625, 11 results** | MRR=0.500, 4 results |
| 0.40 | MRR=0.375, 16 results | **MRR=0.875, 23 results** | MRR=0.750, 16 results |
| 0.45 | MRR=0.442, 30 results | **MRR=0.875, 32 results** | MRR=0.812, 26 results |
| 0.50 | MRR=0.442, 34 results | **MRR=0.875, 39 results** | MRR=0.875, 36 results |

### 6.2. Configuracion ganadora

**`instruct_short` con threshold 0.45**:
- MRR = 0.875 (el resultado #1 es relevante en 7 de 8 queries)
- 32 resultados de media (suficiente pool para paginar)
- Buena precision: R@5 = 4.0, R@10 = 7.1

### 6.3. Instrucciones probadas

| Modo | Prefijo | MRR (th=0.45) |
|------|---------|---------------|
| `raw` | (sin prefijo) | 0.442 |
| `instruct_short` | `Instruct: Retrieve relevant heritage documents.\nQuery: {q}` | **0.875** |
| `instruct_heritage` | `Instruct: Given a web search query, retrieve relevant passages about Spanish cultural heritage.\nQuery: {q}` | 0.812 |
| `instruct_generic` | `Instruct: Given a web search query, retrieve relevant passages.\nQuery: {q}` | 0.680 |

La instruccion corta y directa funciona mejor que las mas elaboradas.

---

## 7. Causa raiz resumida

```
┌──────────────────────────────────────────────────────────────────┐
│  CAUSA RAIZ #1 (impacto critico):                                │
│  La query se envia al embedding service como texto plano.        │
│  Qwen3 la interpreta como un DOCUMENTO, no como una BUSQUEDA.   │
│  El vector resultante esta en la region equivocada del espacio.  │
│                                                                  │
│  Archivo: src/infrastructure/rag/adapters/embedding_adapter.py   │
│  Linea 13: texts se envian tal cual, sin instruccion             │
├──────────────────────────────────────────────────────────────────┤
│  CAUSA RAIZ #2 (impacto medio):                                  │
│  El threshold de 0.25 (similitud coseno >= 0.75) es demasiado    │
│  estricto para Qwen3 incluso con instrucciones.                  │
│                                                                  │
│  Archivo: config/.env → RAG_SIMILARITY_THRESHOLD=0.25            │
└──────────────────────────────────────────────────────────────────┘
```

---

## 8. Cambios propuestos

### 8.1. Critico: Añadir prefijo de instruccion a las queries

**Donde**: `HttpEmbeddingAdapter` o a nivel de use case, antes de llamar al embedding service.

**Que hacer**: cuando se embebe una query (no un documento), wrapear con:
```
Instruct: Retrieve relevant heritage documents.\nQuery: {texto_query}
```

**Importante**: los documentos durante la ingesta NO deben llevar instruccion. Solo las queries.

**Implementacion sugerida**:
- Nueva variable de entorno `EMBEDDING_QUERY_INSTRUCTION` (default: `"Retrieve relevant heritage documents."`)
- El adapter recibe un flag `is_query=False` para saber si debe aplicar el prefijo
- Alternativa mas simple: aplicar el wrapping en el use case antes de llamar a `embed()`

### 8.2. Critico: Subir threshold de similaridad

| Parametro | Valor actual | Valor propuesto | Motivo |
|-----------|-------------|-----------------|--------|
| `RAG_SIMILARITY_THRESHOLD` | 0.25 | **0.45** | Con instrucciones, 0.45 da MRR=0.875 |
| `RAG_SCORE_THRESHOLD` | 0.35 | **0.50** | Recalibrar para modo hibrido con Qwen3 |
| `SEARCH_SCORE_THRESHOLD` | 0.55 | **0.55** | Mantener (ya era mas permisivo) |

### 8.3. No necesario: re-ingesta de documentos

El contenido enriquecido v4 no perjudica la recuperacion. Los 138K chunks se quedan tal cual.

### 8.4. No necesario: cambiar modelo

Qwen3-Embedding-0.6B funciona muy bien cuando se usa correctamente con instrucciones. No hace falta volver a MrBERT.

---

## 9. Impacto esperado

Con los cambios propuestos:

| Query | Score actual (roto) | Score esperado | Resultado #1 esperado |
|-------|--------------------|-|-|
| cuevas del sacromonte | 0.4261 (filtrado) | ~0.36 (pasa 0.45) | Sector Valparaiso-Sacromonte |
| alhambra granada | 0.3722 (filtrado) | ~0.25 (pasa 0.45) | Vista de la Alhambra de Granada |
| mezquita cordoba | 0.4991 (filtrado) | ~0.20 (pasa 0.45) | Mezquita Catedral |
| iglesia barroca sevilla | 0.3542 (filtrado) | ~0.29 (pasa 0.45) | Iglesia de San Ildefonso |
| virgen de la cabeza | ? (0 resultados) | deberia mejorar | (pendiente verificar) |

---

## 10. Scripts de diagnostico

Todos en `backend/scripts/`, ejecutables con `uv run python scripts/<nombre>.py`:

| Script | Que hace |
|--------|---------|
| `embedding_diagnostics.py` | Conecta a BD + embedding service, prueba queries con/sin instruccion, imprime distribuciones de score y sweep de thresholds |
| `create_test_table.py` | Crea tabla `document_chunks_test` con variantes de embedding (baseline vs clean), 500 chunks de 5 provincias |
| `benchmark_retrieval.py` | Benchmark sistematico: discovery mode (encontrar ground truth) y benchmark mode (comparar configs con metricas R@k, MRR) |
| `benchmark_retrieval.py --discover` | Modo descubrimiento: imprime top-20 resultados por query para construir ground truth |

### Prerequisitos para ejecutar los scripts

```bash
# Infra levantada (postgres + embedding service)
make infra

# Datos ingestados en v4
cd backend && make ingest

# Ejecutar diagnostico
cd backend && uv run python scripts/embedding_diagnostics.py
```

---

## 11. Referencia: archivos clave del pipeline

| Archivo | Rol |
|---------|-----|
| `src/infrastructure/rag/adapters/embedding_adapter.py` | Llama al embedding service — **aqui falta la instruccion** |
| `docker/embedding-service/main.py` | Servicio de embedding (correcto, no necesita cambios) |
| `src/infrastructure/rag/adapters/vector_search_adapter.py` | Query pgvector con `<=>` (correcto) |
| `src/domain/rag/services/relevance_filter_service.py` | Filtro `score <= threshold` (correcto, el threshold es el problema) |
| `src/application/search/use_cases/similarity_search_use_case.py` | Use case de busqueda por similaridad |
| `src/application/rag/use_cases/rag_query_use_case.py` | Use case RAG (chat) |
| `src/composition/search_composition.py` | Cableado de search |
| `src/composition/rag_composition.py` | Cableado de RAG |
| `src/config.py` | Parametros (`rag_similarity_threshold`, etc.) |
| `config/.env` | Variables de entorno activas |

---

## 12. Historico de versiones de scoring

Ver `backend/docs/SCORING_VERSIONS.md` para el historico completo de versiones del pipeline (v1-v5). Este diagnostico corresponde a la transicion v5 → v6 donde se incorporara el prefijo de instruccion.
