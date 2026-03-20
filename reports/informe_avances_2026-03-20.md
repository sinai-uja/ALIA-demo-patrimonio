# Informe de Avances 2026-03-20

**Proyecto:** Agente conversacional RAG — Instituto Andaluz de Patrimonio Historico (IAPH)
**Encargo:** Universidad de Jaen
**Rama activa:** `task/14303` · Commit: `e98ceb5`
**Informe anterior:** `informe_desarrollo_2026-03-13` · Commit: `1d9081d` (rama `develop`)

---

## 1. Resumen ejecutivo

Desde el ultimo punto de control (2026-03-13) se han realizado **65+ commits** que incorporan avances significativos en 6 areas: integracion de la API del IAPH, busqueda facetada, reestructuracion de rutas, soporte multi-proveedor LLM, coherencia conversacional y rediseno del frontend.

| Metrica | Antes (13-mar) | Ahora (20-mar) | Delta |
|---------|:--------------:|:--------------:|:-----:|
| Bounded contexts | 4 | **7** | +3 (Heritage, Search, Documents) |
| Endpoints API | 14 | **22** | +8 |
| Heritage assets cargados | 0 | **139.343** | +139K |
| Proveedores LLM | 1 (vLLM) | **2** (vLLM + Gemini) | +1 |
| Migraciones Alembic | 4 | **7** | +3 |
| Paginas frontend activas | 5 | **3** (home, search, routes) | Simplificado |

---

## 2. Punto de control anterior — Estado de TODOs

| TODO | Estado | Fecha |
|------|:------:|:-----:|
| Samuel facilita a Juan Isern acceso a la API del IAPH para descarga de JSON-LD | **Completado** | 2026-03-16 |
| Informar al IAPH de la descarga masiva de datos para evitar bloqueos | **Completado** | 2026-03-16 |
| Juan Isern envia la presentacion HTML a Arturo para compartir con el resto del proyecto | **Completado** | 2026-03-16 |
| Enriquecer datos con la API → heritage_assets | **Completado** | 2026-03-16 |
| ↳ EDA de los datos de la API del IAPH | **Completado** | 2026-03-16 |
| ↳ Integrar informacion georeferenciada en los artefactos de respuesta | **Completado** | 2026-03-16 |
| Probar con encoder alternativo temporal hasta tener el nuevo modelo de UJA → Se usa Gemini | **Completado** | 2026-03-20 |
| Mejorar coherencia conversacional multi-turno con Salamandra | **Completado** | 2026-03-20 |

> Todos los TODOs del punto de control anterior han sido completados.

---

## 3. Avance 1 — Integracion de la API del IAPH (`heritage_assets`)

### 3.1 Nuevo bounded context: Heritage

Se ha creado un bounded context completo para gestionar los datos procedentes de la API publica del IAPH (`https://guiadigital.iaph.es/api/1.0/`).

**Capas implementadas:**

| Capa | Componentes |
|------|-------------|
| Domain | `HeritageAsset` entity, `HeritageRepository` port, value objects tipados por tipo (Inmueble, Mueble, Inmaterial, Paisaje) |
| Application | `GetAssetUseCase`, `ListAssetsUseCase`, `HeritageApplicationService` |
| Infrastructure | `HeritageAssetModel` (SQLAlchemy), `SqlAlchemyHeritageRepository`, scripts de descarga y carga |
| API | `GET /api/v1/heritage` (listado paginado), `GET /api/v1/heritage/{id}` (detalle con typed details) |

**Tabla `heritage_assets`:**

| Columna | Tipo | Descripcion |
|---------|------|-------------|
| `id` | PK | ID del bien en la API IAPH |
| `heritage_type` | str | inmueble/mueble/inmaterial/paisaje |
| `denomination` | str | Nombre del bien |
| `province` | str | Provincia |
| `municipality` | str | Municipio |
| `latitude` / `longitude` | float | Coordenadas (solo 3,4% cubierto) |
| `image_url` | str | URL de imagen principal |
| `image_ids` | ARRAY | IDs de imagenes para galeria |
| `protection` | str | Estado de proteccion legal |
| `raw_data` | JSONB | Respuesta completa de la API (60-110 claves) |

**Comandos:**

```bash
make fetch-assets   # Descarga datos en vivo de la API IAPH (requiere IAPH_API_TOKEN)
make load-assets    # Carga desde ZIP en heritage_assets
```

### 3.2 EDA de los datos de la API del IAPH

Se realizo un analisis exploratorio de datos sobre los 139.343 registros cargados. El documento completo esta en `backend/docs/EDA_IAPH_DATA.md`.

**Distribucion por tipo:**

| Tipo | Registros | % | Claves JSONB (media) |
|------|----------:|--:|:--------------------:|
| Patrimonio Mueble | 107.732 | 77,3% | 63 |
| Patrimonio Inmueble | 29.569 | 21,2% | 74 |
| Patrimonio Inmaterial | 1.924 | 1,4% | 106 |
| Paisaje Cultural | 118 | 0,1% | 8 |

**Completitud de campos:**

| Campo | Mueble | Inmueble | Inmaterial | Paisaje |
|-------|:------:|:--------:|:----------:|:-------:|
| Denominacion | 99,9% | 100% | 100% | 100% |
| Provincia/Municipio | 99,9% | 100% | 100% | Sin municipio |
| Coordenadas (lat/lon) | **0%** | **16,3%** | **0%** | **0%** |
| Imagenes | 66,1% | 46,3% | 94,1% | 100% |
| Descripcion | 86,2% | 95,2% | 100% | Solo PDFs |

**Hallazgos clave:**
- Solo **4.806 bienes** (3,4%) tienen coordenadas — todos de tipo inmueble
- Patrimonio inmaterial es el mas uniformemente completo — ideal para RAG
- El campo de estilo de inmueble esta **94% vacio**
- 14.890 registros de mueble (13,8%) carecen de texto descriptivo
- Paisaje cultural solo contiene enlaces a PDF, sin texto buscable

**Distribucion geografica:**

| Provincia | Total | % |
|-----------|------:|--:|
| Sevilla | 35.312 | 25,3% |
| Cordoba | 22.049 | 15,8% |
| Cadiz | 19.248 | 13,8% |
| Granada | 19.078 | 13,7% |
| Malaga | 16.222 | 11,6% |
| Jaen | 11.093 | 8,0% |
| Huelva | 8.366 | 6,0% |
| Almeria | 7.938 | 5,7% |

---

## 4. Avance 2 — Bounded context Search (busqueda facetada)

Nuevo bounded context para busqueda semantica sobre el catalogo patrimonial con entity detection, filtros facetados, paginacion y enriquecimiento con heritage assets.

### 4.1 Pipeline de busqueda

```
Query → Entity Detection → Embedding → Hybrid Search → RRF Fusion → Relevance Filter → Reranking → Group by document → Asset Enrichment → Paginacion
```

**Configuracion separada del RAG general:**

| Parametro | RAG | Search |
|-----------|:---:|:------:|
| `retrieval_k` | 20 | **200** |
| `score_threshold` | 0.35 | **0.55** |
| `weight_base` | 0.4 | **0.6** |
| `weight_title` | 0.3 | **0.2** |
| `weight_coverage` | 0.2 | **0.15** |
| `weight_position` | 0.1 | **0.05** |

### 4.2 Entity Detection

Servicio de dominio que detecta provincias, municipios y tipos de patrimonio en la query del usuario mediante regex accent-insensitive. Incluye mapeo de keywords (ej. "iglesia" → `patrimonio_inmueble`, "fiesta" → `patrimonio_inmaterial`).

### 4.3 Asset Enrichment

Los resultados de busqueda se enriquecen con datos de `heritage_assets`: denominacion, descripcion, coordenadas, imagen, proteccion. Las imagenes se construyen como URLs del cache IAPH: `https://guiadigital.iaph.es/imagenes-cache/{asset_id}/{image_id}--fic.jpg`.

### 4.4 Endpoints

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| `POST` | `/api/v1/search/similarity` | Busqueda semantica con filtros, paginacion y enrichment |
| `GET` | `/api/v1/search/suggestions` | Deteccion de entidades en texto para sugerencias de filtros |
| `GET` | `/api/v1/search/filters` | Valores disponibles para filtros (provincias, municipios, tipos) |

---

## 5. Avance 3 — Reestructuracion del pipeline de rutas

El pipeline de generacion de rutas se ha rediseñado completamente con un enfoque **stops-first** y generacion estructurada por parada.

### 5.1 Pipeline de 12 pasos

1. Limpiar texto de query (eliminar filtros geograficos redundantes)
2. LLM extrae query de busqueda concisa (max 10 palabras)
3. RAG recupera chunks (`num_stops × 3` para diversidad)
4. **Seleccion de paradas diversas** (round-robin por tipo de patrimonio)
5. Resolver etiqueta de provincia
6. **Enriquecer con heritage assets** — imagenes y coordenadas via `HeritageAssetLookupPort`
7. Construir contexto (solo paradas seleccionadas)
8. LLM genera **JSON estructurado** (no texto libre):
   ```json
   {
     "title": "...",
     "introduction": "...",
     "stops": [{"order": 1, "narrative": "..."}, ...],
     "conclusion": "..."
   }
   ```
9. Parsear JSON para extraer narrativas por parada
10. Componer narrativa monolitica (intro + paradas + conclusion)
11. Construir entidad `VirtualRoute` con detalles de parada (`asset_id`, `narrative_segment`, `image_url`, `lat/lon`)
12. Persistir en BD

### 5.2 Cambios clave

- **Paradas seleccionadas ANTES de la narrativa** → el LLM genera contenido exacto para las paradas elegidas
- **JSON estructurado por parada** → cada parada tiene `order` y `narrative` separados
- **Heritage asset enrichment** → imagenes y coordenadas desde `heritage_assets` (no metadata de chunks)
- **Columnas `introduction`/`conclusion`** en BD → separadas del narrative monolitico
- **Guia interactivo multi-turno** → historial de conversacion, descripciones completas de assets (no RAG)

### 5.3 Guia interactivo mejorado

El guia de ruta ahora usa **descripciones completas de heritage assets** en lugar de chunks RAG, via `HeritageAssetLookupPort.get_asset_full_descriptions()`. Soporta historial de conversacion multi-turno.

### 5.4 Nuevos endpoints

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| `DELETE` | `/api/v1/routes/{id}` | Eliminar ruta |

### 5.5 Dependencias cross-context

Routes ahora depende de:
- **RAG** → recuperacion de chunks para generacion
- **Heritage** → enriquecimiento de paradas (imagenes, coordenadas, descripciones)
- **Search** → entity detection para sugerencias y filter metadata

---

## 6. Avance 4 — Proveedor LLM Gemini

Se ha implementado un adaptador Gemini como alternativa a vLLM/Salamandra, seleccionable via variable de entorno `LLM_PROVIDER`.

### 6.1 Tres adaptadores por contexto

| Contexto | Adaptador | Puerto |
|----------|-----------|--------|
| RAG | `GeminiRAGAdapter` | `LLMPort` — generacion de respuestas |
| Routes | `GeminiRoutesAdapter` | `LLMPort` — generacion estructurada + historial |
| Chat | `GeminiConversationalAdapter` | `ConversationalLLMPort` — clasificacion de intents |

### 6.2 Configuracion

| Variable | Valor por defecto |
|----------|-------------------|
| `LLM_PROVIDER` | `gemini` |
| `GEMINI_API_KEY` | *(requerida)* |
| `GEMINI_MODEL_NAME` | `gemini-3.1-flash-lite-preview` |

El switch se realiza en los ficheros de composicion (`composition/{context}_composition.py`). Los adaptadores vLLM siguen disponibles.

---

## 7. Avance 5 — Coherencia conversacional multi-turno

### 7.1 Historial en guia de rutas

El guia interactivo de rutas ahora mantiene historial de conversacion. El frontend envia los mensajes previos con cada peticion y el adaptador Gemini los incluye en el contexto.

### 7.2 Intent classification en chat

El pipeline de chat usa clasificacion de intents via LLM para decidir si un mensaje es conversacional o una query RAG. Los follow-ups se reformulan con los ultimos 4 mensajes de historial antes de enviarlos al pipeline RAG.

---

## 8. Avance 6 — Rediseno del frontend

### 8.1 Cambios estructurales

- **Homepage simplificada**: solo muestra Busqueda y Rutas Virtuales (eliminados Chat y Accesibilidad)
- **Navegacion reducida**: navbar solo con `/search` (Busqueda) y `/routes` (Rutas)
- **Patron de layout 3 paneles** consistente en search y routes:

```
┌───────────────────────────────────────────────────────┐
│ Drawer (izq)  │  Contenido principal  │  Detail Panel │
│ FilterSidebar │  Input + Resultados   │  AssetDetail  │
│ Collapsible   │                       │  (480px)      │
└───────────────────────────────────────────────────────┘
```

### 8.2 Pagina de busqueda (`/search`) — NUEVA

- **Drawer colapsable** izquierdo con `FilterSidebar` (checkboxes por provincia, municipio, tipo)
- **SmartInput** con deteccion de entidades en tiempo real (tooltips, resaltado por colores)
- **FilterChips** para filtros activos
- **Resultados paginados** con cards enriquecidas (imagen, metadata, coordenadas)
- **Detail Panel** derecho con galeria de imagenes y mapa satelite

### 8.3 Pagina de rutas (`/routes`) — REDISEÑADA

- **RouteSmartInput** con selector de paradas inline (+/- buttons, rango 2-15)
- **Entity detection** para sugerencias de filtros
- **Grid de rutas anteriores** con `RouteCard` (eliminacion con modal de confirmacion custom)
- **Estado vacio** con placeholder cuando no hay rutas
- **RouteDetailPanel** lateral para detalles de asset

### 8.4 Detalle de ruta (`/routes/[id]`) — REDISEÑADO

- **Guia interactivo** en drawer colapsable izquierdo (80px) con historial multi-turno
- **Layout interleaved**: introduction + `RouteStopCard` por parada + conclusion
- **RouteStopCard**: badge numerado, thumbnail, metadata, narrativa
- **Detail Panel** derecho para asset completo de la parada seleccionada
- Soporte dual: formato legacy (narrativa + lista) y nuevo formato interleaved

### 8.5 Componentes compartidos nuevos

| Componente | Uso |
|------------|-----|
| `SmartInput` | Input con entity detection (search + routes) |
| `FilterSidebar` | Sidebar de filtros con checkboxes (search + routes) |
| `FilterChips` | Chips de filtros activos (search + routes) |
| `AssetDetailContent` | Panel de detalle de asset (search + routes) |
| `CollapsibleDrawer` | Drawer con animacion slide (search + routes + route detail) |

### 8.6 Stores Zustand

- **`useSearchStore`**: query, resultados, paginacion, filtros, entidades detectadas, panel de detalle
- **`useRoutesStore`** (actualizado): generacion, numStops, sugerencias, filtros, eliminacion, panel de detalle de parada

---

## 9. Nuevas migraciones Alembic

| # | Revision | Descripcion |
|---|----------|-------------|
| 5 | `b2c3d4e5f6a7` | Crea tabla `heritage_assets` con indices en type, province y GIN en raw_data |
| 6 | `c3d4e5f6a7b8` | Añade FK `document_chunks_v3.document_id` → `heritage_assets.id` |
| 7 | `9af948ad6c54` | Añade columnas `introduction` y `conclusion` a `virtual_routes` |

---

## 10. Gaps actualizados

### Gaps resueltos

| # | Gap original | Resolucion |
|---|-------------|------------|
| G1 | Sin georreferenciacion | **Parcialmente resuelto** — 4.806 inmuebles tienen coordenadas via API IAPH. Geocoding por municipio implementado via Nominatim para fallback. |
| G2 | Tipologia no filtrable | **Resuelto** — `heritage_assets.raw_data` (JSONB con indice GIN) contiene todos los campos de tipologia. Entity detection permite filtrado por tipo, provincia y municipio. |

### Gaps que persisten

| # | Gap | Estado actual |
|---|-----|---------------|
| G3 | Datos sucios (~270 registros) | Persiste — pendiente pipeline de limpieza |
| G4 | Tests minimos | Persiste — ligero aumento pero aun insuficiente |
| G5 | LLM sin fine-tuning | **Mitigado** — Gemini como alternativa temporal. Fine-tuning de Salamandra sigue en progreso |

### Nuevos gaps identificados

| # | Gap | Prioridad |
|---|-----|:---------:|
| G6 | **96,6% de assets sin coordenadas** — solo inmueble tiene datos parciales (16,3%) | Alta |
| G7 | **Paisaje Cultural sin contenido buscable** — solo enlaces a PDF | Media |
| G8 | **Chat y Accesibilidad desactivados en UI** — funcionalidad backend existe pero no se expone | Media |

---

## 11. Proximos pasos

1. **Geocodificacion masiva** — geocodificar assets por municipio+provincia via Nominatim para mejorar cobertura de coordenadas
2. **Extraccion de contenido de PDFs de Paisaje** — parsear PDFs enlazados para enriquecer los 118 registros
3. **Ampliacion de test suite** — tests de integracion para Search y Routes pipelines
4. **Fine-tuning Salamandra** — ajuste al dominio IAPH (en progreso por UJA)
5. **Reactivacion de Chat y Accesibilidad** — evaluar si reintegrar en el frontend

---

*Informe de avances generado automaticamente — Periodo: 2026-03-13 → 2026-03-20 — Rama `task/14303`, commit `e98ceb5`*
