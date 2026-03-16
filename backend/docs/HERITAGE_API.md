# Integración con la API del IAPH

Documentación de la integración con la API de la Guía Digital del IAPH para enriquecer los datos patrimoniales.

## API de origen

- **Base URL:** `https://guiadigital.iaph.es/api/1.0/busqueda`
- **Autenticación:** Bearer token (caduca periódicamente)
- **Formato:** JSON (respuesta Solr: `response.docs[]`, `response.numFound`)
- **Datasets:** `inmueble`, `mueble`, `inmaterial`, `paisaje`

### Ejemplo de petición

```
GET /api/1.0/busqueda/inmueble/rows=500&start=0&q=id:*
Authorization: Bearer {token}
Accept: application/json
```

### Volumen de datos

| Dataset | Registros | Campos Solr | Datos ricos |
|---------|-----------|-------------|-------------|
| inmueble | ~29,500 | ~70 | Todos |
| mueble | ~107,700 | 3-50+ | ~30% (resto solo id + tipo) |
| inmaterial | ~1,900 | ~126 | Todos |
| paisaje | 117 | ~9 | Mínimo (detalle en PDFs) |

## Scripts de carga

### Fetch desde API en vivo

```bash
cd backend
IAPH_API_TOKEN=xxx make fetch-assets
# O directamente:
uv run python -m scripts.fetch_iaph_api --token "TOKEN" --dataset inmueble
```

**Opciones:**
- `--dataset`: `inmueble|mueble|inmaterial|paisaje|all` (default: all)
- `--page-size`: registros por página (default: 500)
- `--delay`: segundos entre peticiones (default: 1.0)

**Comportamiento ante token expirado (401):**
1. Hace commit de los registros descargados hasta el momento
2. Para el dataset actual y salta los restantes
3. Al relanzar: cuenta registros existentes por `heritage_type` y usa ese count como offset inicial
4. Resultado: **reanudación automática** sin re-descargar datos existentes

**Script:** `scripts/fetch_iaph_api.py`

### Carga desde ZIP local

```bash
cd backend
make load-assets
# O directamente:
uv run python -m scripts.load_api_assets --source ../data/API_IAPH.zip
```

Carga los 4 ficheros JSON del ZIP (`inmueble.json`, `mueble.json`, `inmaterial.json`, `paisaje.json`) en la tabla `heritage_assets`.

**Script:** `scripts/load_api_assets.py`

### Idempotencia

Ambos scripts usan `UPSERT` (ON CONFLICT DO UPDATE). Se pueden re-ejecutar sin duplicar datos.

## Tabla `heritage_assets`

Ver esquema completo en [DATA_MODEL.md](DATA_MODEL.md#heritage_assets--datos-enriquecidos-de-la-api-del-iaph).

### Columnas indexadas (acceso directo)

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | String PK | ID numérico del bien en la API |
| `heritage_type` | String | `inmueble`, `mueble`, `inmaterial`, `paisaje` |
| `denomination` | String | Nombre del bien |
| `province` | String | Provincia |
| `municipality` | String | Municipio |
| `latitude` / `longitude` | Float | Coordenadas (solo inmueble parcial) |
| `image_url` | String | URL imagen principal |
| `image_ids` | String[] | UUIDs de imágenes |
| `protection` | String | Estado de protección legal |

### Columna `raw_data` (JSONB)

Almacena el JSON completo de la API (sin `imagen_base64` ni `_version_`). Al servir por la API del backend, se parsea a un modelo tipado distinto según `heritage_type`.

Ver esquema tipado completo en [DATA_MODEL.md](DATA_MODEL.md#esquema-tipado-de-raw_data-por-tipo-patrimonial).

## API REST del backend

### Listado paginado

```
GET /api/v1/heritage?heritage_type=inmueble&province=Jaén&limit=50&offset=0
```

Devuelve resumen (sin `details`) con paginación y total.

### Detalle con datos tipados

```
GET /api/v1/heritage/{id}
```

Devuelve el asset completo con `details` parseado según tipo. El campo `details.type` actúa como discriminante:

- `"inmueble"` → characterisation, typologies, images, bibliography, historical_periods...
- `"mueble"` → measurements, chronology, typologies, images...
- `"inmaterial"` → scope, periodicity, development, origins, clothing, instruments...
- `"paisaje"` → pdf_url, search_terms

## Relación con chunks

`heritage_assets.id` corresponde a la parte numérica de `document_chunks.document_id`:

```
heritage_assets.id = "20831"
document_chunks.document_id = "ficha-inmueble-20831"
```

Esto permite enriquecer las fuentes del RAG con datos del asset (imagen, coordenadas, etc.) si se desea en el futuro.

## Quirks de la API del IAPH

- **Coordenadas invertidas:** En el JSON, `latitud_s` contiene la longitud y `longitud_s` la latitud. Los scripts corrigen esto al extraer.
- **Mueble sparse:** La mayoría de registros mueble solo tienen `id` y `tipo_contenido`. Solo ~30% tienen metadata rica.
- **Paisaje mínimo:** Los datos detallados de paisajes están en PDFs (`pdf_url`), no en el JSON.
- **Arrays paralelos Solr:** Los campos `_smv` son arrays paralelos (ej. `imagen.id_img_smv[0]` + `imagen.titulo_smv[0]` = una imagen). El parser los ensambla en objetos tipados.

## Ficheros clave

| Fichero | Descripción |
|---------|-------------|
| `scripts/fetch_iaph_api.py` | Fetch desde API con paginación y resume |
| `scripts/load_api_assets.py` | Carga desde ZIP, extracción de campos |
| `domain/heritage/value_objects/raw_data.py` | Modelos tipados + parser `parse_raw_data()` |
| `domain/heritage/entities/heritage_asset.py` | Entidad de dominio |
| `infrastructure/heritage/repositories/heritage_repository.py` | Repo SQLAlchemy |
| `api/v1/endpoints/heritage/schemas.py` | Schemas Pydantic |
| `api/v1/endpoints/heritage/heritage.py` | Endpoints REST |
