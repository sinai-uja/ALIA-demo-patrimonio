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

El grueso de los ~6.5s restantes es latencia de red + inferencia en Cloud Run (GPU L4).
Eso es irreducible desde el backend.
