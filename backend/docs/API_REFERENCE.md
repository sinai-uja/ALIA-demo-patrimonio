# Referencia de la API

Base URL: `http://localhost:8080/api/v1`

OpenAPI interactivo: `http://localhost:8080/docs`

## Endpoints

### RAG

#### `POST /rag/query`

Consulta RAG directa (sin contexto conversacional).

**Request:**
```json
{
  "query": "iglesias renacentistas en Jaén",
  "top_k": 5,
  "heritage_type_filter": "patrimonio_inmueble",
  "province_filter": "Jaén"
}
```

**Response:**
```json
{
  "answer": "En Jaén se encuentran varias iglesias renacentistas destacadas [1]...",
  "sources": [
    {
      "title": "Catedral de la Asunción de la Virgen",
      "url": "https://guiadigital.iaph.es/...",
      "score": 0.12,
      "heritage_type": "patrimonio_inmueble",
      "province": "Jaén",
      "municipality": "Jaén",
      "metadata": { "characterisation": "Arquitectónica" }
    }
  ],
  "query": "iglesias renacentistas en Jaén",
  "abstained": false
}
```

---

### Chat

#### `POST /chat/sessions`

Crea una nueva sesión de conversación.

**Request:** `{ "title": "Consulta sobre patrimonio" }`

**Response:** `{ "id": "uuid", "title": "...", "created_at": "...", "updated_at": "..." }`

#### `GET /chat/sessions`

Lista todas las sesiones.

#### `GET /chat/sessions/{id}`

Obtiene una sesión.

#### `PATCH /chat/sessions/{id}`

Actualiza el título. **Request:** `{ "title": "Nuevo título" }`

#### `DELETE /chat/sessions/{id}`

Elimina una sesión y todos sus mensajes (CASCADE).

#### `GET /chat/sessions/{session_id}/messages`

Lista mensajes de una sesión.

#### `POST /chat/sessions/{session_id}/messages`

Envía un mensaje. Activa el pipeline RAG y devuelve la respuesta del asistente.

**Request:**
```json
{
  "content": "háblame de la Alhambra",
  "top_k": 5,
  "heritage_type_filter": null,
  "province_filter": "Granada"
}
```

**Response:**
```json
{
  "id": "uuid",
  "role": "assistant",
  "content": "La Alhambra es un conjunto monumental [1]...",
  "sources": [ ... ],
  "created_at": "2026-03-16T..."
}
```

---

### Heritage Assets

#### `GET /heritage`

Lista assets patrimoniales con filtros y paginación. Devuelve resumen (sin `details`).

**Query params:**

| Param | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `heritage_type` | string | null | `inmueble`, `mueble`, `inmaterial`, `paisaje` |
| `province` | string | null | Filtro por provincia |
| `municipality` | string | null | Filtro por municipio |
| `limit` | int | 50 | Tamaño de página (1-200) |
| `offset` | int | 0 | Offset para paginación |

**Response:**
```json
{
  "items": [
    {
      "id": "20831",
      "heritage_type": "inmueble",
      "denomination": "Catedral de Jaén",
      "province": "Jaén",
      "municipality": "Jaén",
      "latitude": 37.765,
      "longitude": -3.789,
      "image_url": "https://guiadigital.iaph.es/sites/default/files/...",
      "protection": "BIC"
    }
  ],
  "total": 29569,
  "limit": 50,
  "offset": 0
}
```

#### `GET /heritage/{id}`

Detalle completo de un asset con `details` tipado según `heritage_type`.

**Response:** Asset completo con campo `details` polimórfico. El campo `details.type` indica el tipo:

- `"inmueble"`: `characterisation`, `postal_address`, `historical_data`, `description`, `protection`, `typologies[]`, `images[]`, `bibliography[]`, `related_assets[]`, `historical_periods[]`
- `"mueble"`: `measurements`, `chronology`, `description`, `protection`, `typologies[]`, `images[]`, `bibliography[]`, `related_assets[]`
- `"inmaterial"`: `scope`, `framework_activities`, `activity_dates`, `periodicity`, `district`, `description`, `development`, `spatial_description`, `agents_description`, `evolution`, `origins`, `preparations`, `clothing`, `instruments`, `transmission_mode`, `transformations`, `protection`, `typologies[]`, `images[]`, `bibliography[]`, `related_assets[]`
- `"paisaje"`: `pdf_url`, `search_terms[]`

---

### Routes

#### `GET /routes/suggestions`

Detecta entidades (provincias, municipios, tipos de patrimonio) en un texto de búsqueda de rutas. Reutiliza la detección de entidades del contexto de búsqueda.

**Query params:** `?query=castillos en Jaén y Córdoba`

**Response:**
```json
{
  "query": "castillos en Jaén y Córdoba",
  "search_label": "castillos",
  "detected_entities": [
    { "entity_type": "province", "value": "Jaén", "display_label": "Jaén", "matched_text": "Jaén" },
    { "entity_type": "province", "value": "Córdoba", "display_label": "Córdoba", "matched_text": "Córdoba" }
  ]
}
```

#### `GET /routes/filters`

Devuelve los valores disponibles para los filtros de generación de rutas.

**Query params opcionales:** `?provinces=Jaén` (filtra municipios por provincia).

**Response:**
```json
{
  "heritage_types": ["PATRIMONIO_INMUEBLE", "PATRIMONIO_MUEBLE", ...],
  "provinces": ["Almería", "Cádiz", ...],
  "municipalities": ["Jaén", "Úbeda", ...]
}
```

#### `POST /routes/generate`

Genera una ruta virtual personalizada. Pipeline: limpiar texto → extraer query vía LLM → RAG con filtros → generar narrativa vía LLM.

**Request:**
```json
{
  "query": "arte renacentista en la provincia de Jaén",
  "num_stops": 5,
  "heritage_type_filter": ["PATRIMONIO_INMUEBLE"],
  "province_filter": ["Jaén"],
  "municipality_filter": null
}
```

**Response:** Objeto `VirtualRoute` con `id`, `title`, `province`, `stops[]`, `narrative`, `introduction`, `conclusion`, `total_duration_minutes`, `created_at`.

Cada stop incluye: `order`, `title`, `heritage_type`, `province`, `municipality`, `url`, `description`, `visit_duration_minutes`, `heritage_asset_id`, `narrative_segment`, `image_url`, `latitude`, `longitude`.

#### `GET /routes`

Lista rutas. Filtro opcional: `?province=Jaén`.

#### `GET /routes/{id}`

Detalle de una ruta.

#### `DELETE /routes/{id}`

Elimina una ruta virtual. Devuelve `204 No Content` si se elimina correctamente, `404` si no existe.

#### `POST /routes/{id}/guide`

Pregunta al guía interactivo sobre una ruta. El guía solo responde sobre las paradas de la ruta; si la pregunta es sobre algo externo, sugiere usar la búsqueda o crear una nueva ruta.

**Request:** `{ "question": "¿Cuál es la parada más importante?" }`

**Response:** `{ "answer": "..." }`

---

### Accessibility

#### `POST /accessibility/simplify`

Simplifica texto a Lectura Fácil.

**Request:**
```json
{
  "text": "Texto complejo sobre patrimonio...",
  "level": "basic",
  "document_id": null
}
```

**Response:** `{ "original_text": "...", "simplified_text": "...", "level": "basic", "document_id": null }`

---

### Documents

#### `POST /documents/ingest`

Ingesta un dataset de parquet.

**Request:**
```json
{
  "source_path": "../data/Guia_Digital_Patrimonio_Andalucia/Guia_Digital_Patrimonio_Inmueble.parquet",
  "heritage_type": "patrimonio_inmueble"
}
```

#### `GET /documents/chunks/{document_id}`

Obtiene los chunks de un documento.

---

### Health

#### `GET /health`

```json
{ "status": "ok", "service": "UJA-IAPH RAG" }
```

## Códigos de error

| Código | Significado |
|--------|-------------|
| 400 | Request inválida (validación Pydantic) |
| 404 | Recurso no encontrado (asset, sesión, ruta) |
| 502 | Error en servicio externo (LLM, embedding) |
| 500 | Error interno |

## Formato de errores

```json
{ "detail": "Asset not found" }
```
