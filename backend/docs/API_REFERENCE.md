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

#### `POST /routes/generate`

Genera una ruta virtual personalizada.

**Request:**
```json
{
  "province": "Jaén",
  "num_stops": 5,
  "heritage_types": ["patrimonio_inmueble", "patrimonio_mueble"],
  "user_interests": "arte renacentista"
}
```

**Response:** Objeto `VirtualRoute` con `id`, `title`, `stops[]`, `narrative`, `total_duration_minutes`.

#### `GET /routes`

Lista rutas. Filtro opcional: `?province=Jaén`.

#### `GET /routes/{id}`

Detalle de una ruta.

#### `POST /routes/{id}/guide`

Pregunta al guía sobre una ruta.

**Request:** `{ "question": "¿Cuál es la parada más importante?" }`

**Response:** `{ "answer": "...", "sources": [...] }`

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
