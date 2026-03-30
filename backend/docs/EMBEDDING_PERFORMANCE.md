# Embedding Service Performance

Benchmark de latencia del endpoint `/api/v1/search/similarity` con el embedding service
desplegado en **Cloud Run** (europe-west1, GPU L4).

- **Query**: `"cuevas del sacromonte"`
- **Peticiones por ronda**: 10
- **Fecha**: 2026-03-30

## Resultados

| Optimizacion | p50 (ms) | p95 (ms) | Media (ms) | Min (ms) | Max (ms) |
|---|---:|---:|---:|---:|---:|
| Baseline (sin cambios) | 7194 | 25161 | 8984 | 7096 | 25161 |
| + httpx client reutilizado | 7151 | 7247 | 7161 | 7067 | 7247 |
| + token provider singleton (lru_cache) | 6776 | 6937 | 6789 | 6712 | 6937 |
| + adapters singleton (module-level) | 6659 | 6959 | 6657 | 6534 | 6959 |

## Analisis

### Baseline

La primera peticion tarda ~25s porque:
1. Se crea un nuevo `GcpIdentityTokenProvider` por cada request (composiciones reconstruidas via `Depends()`)
2. Se crea un nuevo `httpx.AsyncClient` por cada llamada (handshake TCP+TLS)
3. El identity token de GCP se fetchea en cada request (el cache es per-instance, no global)

Las peticiones siguientes (~7.1s) ya tienen el token en cache de la instancia creada para ese request,
pero siguen pagando el coste de crear un nuevo client HTTP.

### Opt 1: httpx client reutilizado

Se elimina el `async with httpx.AsyncClient()` por cada llamada y se usa un client persistente
en el adapter. El connection pool de httpx reutiliza la conexion TCP+TLS.

- **p95**: 25161 → 7247 ms (-71%)
- **Media**: 8984 → 7161 ms (-20%)
- El spike de la primera peticion desaparece (no hay cold handshake)

### Opt 2: token provider singleton (lru_cache)

`build_token_provider()` se cachea con `@lru_cache`. La misma URL devuelve la misma instancia
de `GcpIdentityTokenProvider`, preservando el cache del identity token entre requests.

- **Media**: 7161 → 6789 ms (-5%)
- Eliminacion del fetch de identity token en cada request

### Opt 3: adapters singleton (module-level)

Los adapters HTTP (embedding, reranker, LLM) y servicios de dominio sin estado se crean
como singletons a nivel de modulo en las composiciones. Solo los adapters que necesitan
`AsyncSession` (DB) se crean per-request.

- **Media**: 6789 → 6657 ms (-2%)
- Elimina la reconstruccion innecesaria del grafo de dependencias en cada request

### Resumen

| Metrica | Antes | Despues | Mejora |
|---------|------:|--------:|-------:|
| Primera peticion (p95) | 25161 ms | 6959 ms | **-72%** |
| Latencia tipica (p50) | 7194 ms | 6659 ms | **-7%** |
| Media | 8984 ms | 6657 ms | **-26%** |

El grueso de los ~6.5s restantes es latencia de red + reranking de 50 documentos en Cloud Run (GPU L4).

---

## Reranker batch size

Con el reranker activado (`RERANKER_ENABLED=true`, `RERANKER_TOP_N=50`, Qwen3-Reranker-0.6B en L4),
se testeo el impacto del `RERANKER_BATCH_SIZE` en el servicio de embedding.

### Resultados

| Batch size | p50 (ms) | p95 (ms) | Media (ms) | Min (ms) | Max (ms) |
|---:|---:|---:|---:|---:|---:|
| **1** | **3606** | **6597** | **3905** | **3589** | **6597** |
| 2 | 4691 | 7561 | 4969 | 4633 | 7561 |
| 4 | 6455 | 9029 | 6705 | 6385 | 9029 |
| 8 | 9664 | 12671 | 9952 | 9575 | 12671 |
| 16 | OOM | OOM | OOM | OOM | OOM |

### Por que batch mayor es mas lento

Resultado contraintuitivo: mas paralelismo GPU deberia ser mas rapido. Pero el codigo actual
usa `padding=True` en `apply_chat_template()`, lo que rellena **todas las secuencias del batch
a la longitud de la mas larga**. Con chunks de ~1000-1200 tokens con varianza alta en longitud:

- Un chunk corto de 200 tokens se infla a 1200 tokens de padding
- El computo de atencion es O(n^2) en la longitud de secuencia
- Mas pares por batch = mas padding desperdiciado = mas VRAM y computo inutil
- Con batch=16, el padding inflado causa CUDA OOM (intenta alocar 19.25 GB)

Con batch=1 no hay padding: cada forward pass procesa exactamente los tokens necesarios.
50 forward passes minimos son mas rapidos que 13 batches inflados (batch=4) o 7 (batch=8).

### Propuestas de mejora

Para que el batching funcione y se aproveche el paralelismo de la GPU, hay dos enfoques:

**1. Sorted batching** — cambio en `_score_pairs()` de `embedding/main.py`:

1. Pre-tokenizar los pares para conocer su longitud real
2. Ordenar por longitud de tokens antes de agrupar en batches
3. Los pares de longitud similar caen en el mismo batch → padding minimo
4. Tras el scoring, reordenar los resultados al orden original

Con esto, batch=4-8 tendria padding despreciable y ganaria paralelismo real.

**2. Dynamic padding con buckets** — cambio mas ambicioso:

1. Definir buckets de longitud (ej. 0-256, 256-512, 512-1024, 1024+)
2. Asignar cada par a su bucket
3. Procesar cada bucket con su propio batch y padding ajustado al bucket
4. Combinar resultados

Mas complejo pero optimo: cada par se rellena como maximo hasta el techo de su bucket,
no hasta el maximo del batch.

Ambos enfoques requieren cambios en el servicio de embedding (`embedding/main.py`),
no en la configuracion. El beneficio esperado: batch=4-8 con rendimiento similar o
mejor que batch=1 actual, gracias a paralelismo GPU sin overhead de padding.

### Configuracion optima actual

`RERANKER_BATCH_SIZE=1` — sin padding, minimo computo por forward pass.

### Resumen final (con todas las optimizaciones)

| Metrica | Baseline original | Final (opts + batch=1) | Mejora |
|---------|------------------:|-----------------------:|-------:|
| Primera peticion (p95) | 25161 ms | 6597 ms | **-74%** |
| Latencia tipica (p50) | 7194 ms | 3606 ms | **-50%** |
| Media | 8984 ms | 3905 ms | **-57%** |
