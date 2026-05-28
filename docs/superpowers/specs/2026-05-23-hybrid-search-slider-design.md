# Híbrido configurable por slider — Diseño

> Spec de diseño. Próximo paso: writing-plans → implementación.

## Contexto

Tras la reunión con UJA del 25-mayo, Arturo decide reactivar la búsqueda híbrida (lexical + semántica) y añadir un control en la UI para alternar el peso. En vez de un toggle binario (100% semántico vs 50/50), se opta por un **slider continuo** que controle la ponderación lexical / semántica de cada búsqueda.

Adicionalmente, durante el diseño se identifica que el reranker SINAI **debe aplicarse antes de la fusión** y **solo sobre el carril semántico**, en vez de después de la fusión sobre todos los chunks. Esto resuelve el caso "Zurbarán" (palabra clave que el reranker hunde si toca a chunks lexicales).

Decisiones descartadas por Arturo (registradas como ideas para futuro proyecto):
- Fusión por intersección.
- Ponderación dinámica por longitud de query.
- Triage / clasificación de query.

## Objetivos

1. Permitir al usuario elegir en cada búsqueda la mezcla lexical/semántica vía un slider.
2. Resolver el caso "Zurbarán" (queries de 1 token) sin tener que apagar el reranker globalmente.
3. Mantener compatibilidad: clientes que no envíen `lexical_weight` siguen funcionando con el comportamiento actual configurado por `.env`.

## No-objetivos

- Triage de query, heurísticas de longitud, intersección de listados (descartados por Arturo).
- Cambiar la lógica del RAG (chat / rutas). El slider aplica a Search; RAG sigue con su flag global.
- Reentrenar embeddings o reranker.

## Arquitectura

### Cambio de orden en el pipeline

**Antes (similarity-only + reranker):**
```
vector ─> rerank ─> filter
```

**Antes (hybrid):**
```
vector ─┐
        ├─> RRF fuse (text_weight=1.5) ─> rerank ─> filter
text  ──┘
```

**Después (unificado):**
```
vector ─> rerank ─> ranks calibrados ──┐
                                        ├─> RRF ponderada por lexical_weight ─> filter
text  ─────────> tsvector ranks ───────┘
```

Razón del orden:
- El reranker es una **herramienta de precisión semántica**. Su valor está en calibrar la ambigüedad del embedding.
- El text-search es **evidencia lexical fiable**. No requiere recalibración por cross-encoder.
- Aplicar el reranker tras la fusión hace que penalice falsamente los matches lexicales en queries cortas tipo "Zurbarán".

### Parámetro `lexical_weight ∈ [0, 1]`

| Valor | Interpretación | Llamadas backend |
|---|---|---|
| `0.0` | 100% semántico | Solo vector + rerank |
| `0.5` | Mezcla equilibrada | Vector + rerank + text + fusión |
| `1.0` | 100% lexical | Solo text |
| `0.3` | Mayoritariamente semántico | Vector + rerank + text + fusión (semantic weight = 0.7) |

`semantic_weight = 1 - lexical_weight`. El slider es una única palanca conceptual.

### Fórmula RRF nueva

```
rrf_score(chunk) = semantic_weight * (1 / (60 + rank_in_reranked_vector)) +
                   lexical_weight  * (1 / (60 + rank_in_text))
```

Se sigue normalizando a distancia coseno (0 = mejor) para mantener la semántica del filtro `score_threshold` aguas abajo.

### Backward compatibility

- Si `lexical_weight` NO viene en el request → backend usa `settings.search_default_lexical_weight`.
- Si `settings.rag_similarity_only = true` Y `lexical_weight` NO viene → se fuerza `0.0`.
- Si `settings.rag_similarity_only = true` Y `lexical_weight` SÍ viene → gana el request (la decisión del usuario sobrescribe la default).

## Contrato API

### `POST /api/v1/search/similarity`

Schema actualizado:

```python
class SimilaritySearchRequestSchema(BaseModel):
    query: str
    page: int = 1
    page_size: int = 10
    heritage_type_filter: str | None = None
    province_filter: str | None = None
    municipality_filter: str | None = None
    score_threshold: float | None = None
    lexical_weight: float | None = None   # ← nuevo, opcional, [0.0, 1.0]
```

Validación: `0.0 <= lexical_weight <= 1.0`. Fuera de rango → 422.

## Frontend

### Componente `LexicalWeightControl`

Clonado de `ScoreThresholdControl` con misma estructura (variantes `stacked` / `inline`, botones +/-, slider HTML range, input numérico):

- Rango: `[0.0, 1.0]`, step `0.05`.
- Etiqueta: "Ponderación de la búsqueda".
- Pie: "Más semántica ← → más lexical".
- Mostrar siempre ambos pesos en el header: `Semántica 0.30 · Lexical 0.70`.
- Persistencia: localStorage `search:lexicalWeight` y `routes:lexicalWeight`.

### Integración

- Página `/search` y `/routes`: render del control junto al de threshold.
- Store `search.ts` y `routes.ts`: nuevo estado `lexicalWeight`, setter, persist.
- `searchApi.similarity()` envía `lexical_weight` en cada request.

## Defaults vía env

### Backend

```env
# backend/.env
SEARCH_DEFAULT_LEXICAL_WEIGHT=0.5
```

Nuevo campo `search_default_lexical_weight: float = 0.5` en `Settings`.

### Frontend

```env
# frontend/.env.local (inyectada runtime por el entrypoint Docker, igual que NEXT_PUBLIC_API_URL)
NEXT_PUBLIC_DEFAULT_LEXICAL_WEIGHT=0.5
```

Store:
```typescript
const DEFAULT_LEXICAL_WEIGHT = Number(
  process.env.NEXT_PUBLIC_DEFAULT_LEXICAL_WEIGHT ?? "0.5"
);
```

## Cambios concretos por archivo

### Backend

| Archivo | Cambio |
|---|---|
| `src/config.py` | Añadir `search_default_lexical_weight: float = 0.5` |
| `src/application/search/dto/search_dto.py` | Añadir `lexical_weight: float \| None` al `SimilaritySearchDTO` |
| `src/api/v1/endpoints/search/schemas.py` | Añadir `lexical_weight: float \| None` con validación `ge=0, le=1` |
| `src/api/v1/endpoints/search/search.py` | Propagar el campo al DTO |
| `src/domain/rag/services/hybrid_search_service.py` | `fuse()` recibe `lexical_weight: float`; eliminar `text_weight` del constructor |
| `src/application/search/use_cases/similarity_search_use_case.py` | Refactor: un único flujo controlado por `lexical_weight`. Reranker se aplica antes de la fusión, solo sobre `vector_chunks` |

### Frontend

| Archivo | Cambio |
|---|---|
| `frontend/components/shared/LexicalWeightControl.tsx` | Nuevo, clonado de ScoreThresholdControl |
| `frontend/store/search.ts` | Estado `lexicalWeight`, setter, persistir en localStorage, pasar al API |
| `frontend/store/routes.ts` | Igual que search |
| `frontend/app/search/page.tsx` | Render del control |
| `frontend/app/routes/page.tsx` | Render del control |
| `frontend/lib/api.ts` | Añadir `lexical_weight` al payload de `searchApi.similarity` |
| `frontend/Dockerfile` / entrypoint | Inyectar `NEXT_PUBLIC_DEFAULT_LEXICAL_WEIGHT` en runtime |

### Config / docs

| Archivo | Cambio |
|---|---|
| `backend/config/.env.example` | Documentar `SEARCH_DEFAULT_LEXICAL_WEIGHT` |
| `frontend/config/.env.example` | Documentar `NEXT_PUBLIC_DEFAULT_LEXICAL_WEIGHT` |
| `CLAUDE.md` | Documentar la nueva env var + el nuevo pipeline |
| `docker-compose.yml` | Añadir vars |

## Tests

- Unit `HybridSearchService.fuse`:
  - `lexical_weight=0.0` → ranking idéntico al vector_results.
  - `lexical_weight=1.0` → ranking idéntico al text_results.
  - `lexical_weight=0.5` → mezcla.
- Integration `SimilaritySearchUseCase`:
  - Sin `lexical_weight` en DTO + `RAG_SIMILARITY_ONLY=true` → comportamiento idéntico al actual.
  - `lexical_weight=1.0` → no se llama a vector_search ni al embedding.
  - `lexical_weight=0.0` → no se llama a text_search.
  - Reranker se aplica antes de la fusión cuando `lexical_weight ∈ (0, 1)`.

## Riesgos

1. **Calibración del threshold**: el slider del score_threshold vive en un régimen distinto si el modo es híbrido (RRF normalizado) vs semántico puro (rerank score). Posible mitigación: mostrar al usuario en el helper text de qué tipo de score se trata, y mantener el default 0.5 que funciona razonablemente en ambos.
2. **Latencia del reranker en queries semánticas dominantes**: el rerank se aplica siempre que `lexical_weight < 1.0`. Para queries con `lexical_weight=0.95`, llamar al rerank por unos pocos chunks que apenas contribuyen es ineficiente. Mitigación futura (no en esta release): umbral de bypass.
3. **Compatibilidad con consumo no-UI**: si hay otros clientes del endpoint que no envían `lexical_weight`, heredan el default del backend. No rompe nada.

## Plan de despliegue

1. Backend: cambios + tests.
2. Frontend: componente + integración.
3. Build + push imagen 1.1.2.
4. En remoto: actualizar `docker-compose.yml`, añadir vars al `.env`, `docker compose up -d --force-recreate backend frontend`.
5. Validación manual contra el documento del IAPH (Zurbarán, Inventario, almohade, Fortuny, Vanitas, carnaval).
