# Versionado de Document Chunks

La tabla `document_chunks` utiliza un esquema de versionado (`document_chunks_v1`, `document_chunks_v2`, etc.) para que distintas estrategias de chunking coexistan en la base de datos sin perdida de datos.

## Tabla resumen

| Version | Tabla | Estrategia de chunking | Contenido del embedding | Tamano chunk | Overlap | Registros |
|---------|-------|------------------------|-------------------------|--------------|---------|-----------|
| v1 | `document_chunks_v1` | Ventana fija por palabras | Solo texto del chunk | 512 palabras | 64 | ~149,290 |
| v2 | `document_chunks_v2` | Por parrafos (respeta `\n\n`) | Metadata basica + texto | 1024 palabras | 128 | Pendiente de ingesta |
| v3 | `document_chunks_v3` | Por parrafos (respeta `\n\n`) | Metadata tipo-especifica + texto | 1024 palabras | 128 | Pendiente de ingesta |
| v4 | `document_chunks_v4` | Por parrafos (respeta `\n\n`) | Plantilla lenguaje natural + texto | 1024 palabras | 128 | Pendiente de ingesta |

## Como cambiar de version

Configurar la variable de entorno `CHUNKS_TABLE_VERSION` en `backend/config/.env`:

```bash
# Usar v1 (chunking original)
CHUNKS_TABLE_VERSION=v1

# Usar v2 (chunking por parrafos + embeddings enriquecidos con metadata basica)
CHUNKS_TABLE_VERSION=v2

# Usar v3 (v2 + metadata tipo-especifica en content + columna metadata JSONB)
CHUNKS_TABLE_VERSION=v3
```

Reiniciar el backend tras el cambio. No hace falta migracion ni re-ingesta para cambiar — ambas tablas coexisten.

## Versiones

### v1 — Chunking por ventana de palabras (original)

- **Tabla**: `document_chunks_v1`
- **Estrategia**: Ventanas fijas de palabras (512 palabras, 64 de solapamiento)
- **Contenido del embedding**: Solo el texto crudo del chunk
- **Registros**: ~149,290 chunks de los 4 datasets
- **Creada**: Ingesta inicial

### v2 — Chunking por parrafos + enriquecimiento de metadata

- **Tabla**: `document_chunks_v2`
- **Estrategia**: Division por parrafos (respeta limites `\n\n`, nunca corta a mitad de parrafo). Si un parrafo supera el tamano maximo, se aplica fallback a division por palabras.
- **Contenido del embedding**: Se antepone una cabecera de metadata antes de generar el embedding:
  ```
  Titulo: X | Tipo: Y | Provincia: Z | Municipio: W
  ---
  {contenido del chunk}
  ```
  Esto mejora la recuperacion para consultas por nombre propio o ubicacion.
- **Configuracion recomendada**:
  ```bash
  RAG_CHUNK_SIZE=1024
  RAG_CHUNK_OVERLAP=128
  CHUNKS_TABLE_VERSION=v2
  ```
- **Registros**: Vacia hasta ejecutar `make ingest` con `CHUNKS_TABLE_VERSION=v2`

## Como ingestar en v2

1. Aplicar la migracion:
   ```bash
   make migrate
   ```

2. Configurar variables de entorno en `backend/config/.env`:
   ```bash
   CHUNKS_TABLE_VERSION=v2
   RAG_CHUNK_SIZE=1024
   RAG_CHUNK_OVERLAP=128
   ```

3. Ejecutar la ingesta:
   ```bash
   cd backend && make ingest
   ```

4. Verificar:
   ```sql
   SELECT COUNT(*) FROM document_chunks_v2;
   ```

### v3 — Metadata tipo-especifica en content + columna JSONB

- **Tabla**: `document_chunks_v3`
- **Estrategia**: Misma que v2 (parrafos, sin cortar a mitad de parrafo)
- **Contenido del embedding**: Cabecera enriquecida con campos tipo-especificos del parquet:
  ```
  Titulo: X | Tipo: Y | Provincia: Z | Municipio: W | Autor: A | Estilo: B | Periodo: C
  ---
  {contenido del chunk}
  ```
- **Campos de enrichment por tipo de activo**:

  | Tipo patrimonial | Campos en cabecera |
  |------------------|--------------------|
  | Patrimonio Mueble | authors, styles, historic_periods, chronology, materials, techniques, type, protection, iconographies |
  | Patrimonio Inmueble | characterisation, protection |
  | Patrimonio Inmaterial | activity_types, subject_topic |
  | Paisaje Cultural | topic, landscape_demarcation |

- **Columna `metadata` JSONB**: Almacena TODOS los campos extra del parquet (tanto los de enrichment como los de solo display: code, dimensions, sources, description, etc.). Disponible para la UI del frontend.
- **Configuracion recomendada**:
  ```bash
  CHUNKS_TABLE_VERSION=v3
  RAG_CHUNK_SIZE=1024
  RAG_CHUNK_OVERLAP=128
  ```
- **Registros**: Vacia hasta ejecutar `make ingest` con `CHUNKS_TABLE_VERSION=v3`

## Como ingestar en v3

1. Aplicar la migracion:
   ```bash
   make migrate
   ```

2. Configurar variables de entorno en `backend/config/.env`:
   ```bash
   CHUNKS_TABLE_VERSION=v3
   RAG_CHUNK_SIZE=1024
   RAG_CHUNK_OVERLAP=128
   ```

3. Ejecutar la ingesta:
   ```bash
   cd backend && make ingest
   ```

4. Verificar:
   ```sql
   SELECT COUNT(*) FROM document_chunks_v3;
   -- Verificar cabecera en content
   SELECT LEFT(content, 200) FROM document_chunks_v3 LIMIT 1;
   -- Verificar metadata JSONB
   SELECT metadata FROM document_chunks_v3 LIMIT 1;
   ```

### v4 — Plantillas en lenguaje natural + encoder configurable (MrBERT / Qwen3)

- **Tabla**: `document_chunks_v4`
- **Estrategia**: Misma que v2/v3 (parrafos, sin cortar a mitad de parrafo)
- **Encoder soportado**: MrBERT (768 dims) o **Qwen/Qwen3-Embedding-0.6B** (1024 dims), seleccionable por variable de entorno
- **Contenido del embedding**: Plantillas en lenguaje natural por tipo patrimonial, seguidas del fragmento de texto:

  **Paisaje Cultural:**
  ```
  Paisaje cultural titulado '{title}' y ubicado en la provincia de '{province}'.
  {texto del chunk}
  ```

  **Bien Inmaterial:**
  ```
  Bien inmaterial titulado '{title}', clasificado como {activity_types} bajo la categoría {subject_topic}. Ubicado en {district}, {municipality}, {province}.
  {texto del chunk}
  ```

  **Bien Inmueble:**
  ```
  Bien inmueble titulado '{title}'. Es una propiedad de naturaleza {characterisation} y tipo {type}. Ubicado en el municipio de {municipality}, provincia de {province}.
  De estilo {style} y período histórico {historic_periods}.
  {texto del chunk}
  ```

  **Bien Mueble:**
  ```
  Bien mueble titulado '{title}' de tipo {type}. Ubicado en el municipio de {municipality}, provincia de {province}.
  De estilo {style} y período histórico {historic_periods}.
  {texto del chunk}
  ```

  > Campos ausentes se omiten automaticamente de la plantilla.

- **Columna `metadata` JSONB**: Igual que v3, almacena TODOS los campos extra del parquet.
- **Campos de metadata JSONB por tipo** (segun especificacion de Samuel Sanchez):

  | Tipo patrimonial | Campos en metadata JSONB |
  |------------------|--------------------------|
  | Paisaje Cultural | landscape_demarcation, area, topic |
  | Patrimonio Inmaterial | subject_topic, activity_types, district, date, frequency |
  | Patrimonio Inmueble | code, characterisation |
  | Patrimonio Mueble | code, type, disciplines, historic_periods, styles, chronology, iconographies, authors, materials, techniques, dimensions, protection |

- **Configuracion para MrBERT** (retrocompatible):
  ```bash
  CHUNKS_TABLE_VERSION=v4
  EMBEDDING_MODEL_DIR=MrBERT
  POOLING_STRATEGY=mean
  MAX_LENGTH=8192
  EMBEDDING_DIM=768
  RAG_CHUNK_SIZE=1024
  RAG_CHUNK_OVERLAP=128
  ```

- **Configuracion para Qwen3-Embedding-0.6B** (recomendada):
  ```bash
  CHUNKS_TABLE_VERSION=v4
  EMBEDDING_MODEL_DIR=Qwen3-Embedding-0.6B
  POOLING_STRATEGY=last_token
  MAX_LENGTH=32768
  EMBEDDING_DIM=1024
  RAG_CHUNK_SIZE=1024
  RAG_CHUNK_OVERLAP=128
  ```

## Como ingestar en v4

1. (Opcional) Descargar modelo Qwen3:
   ```bash
   cd backend && make download-qwen3
   ```

2. Aplicar la migracion:
   ```bash
   make migrate
   ```

3. Configurar variables de entorno en `backend/config/.env` (elegir encoder):
   ```bash
   CHUNKS_TABLE_VERSION=v4
   # Para Qwen3:
   EMBEDDING_MODEL_DIR=Qwen3-Embedding-0.6B
   POOLING_STRATEGY=last_token
   MAX_LENGTH=32768
   EMBEDDING_DIM=1024
   RAG_CHUNK_SIZE=1024
   RAG_CHUNK_OVERLAP=128
   ```

4. Reconstruir el servicio de embeddings si se cambio de encoder:
   ```bash
   docker compose -f docker/docker-compose.yml build embedding-service
   ```

5. Ejecutar la ingesta:
   ```bash
   cd backend && make ingest
   ```

6. Verificar:
   ```sql
   -- Verificar plantilla en content
   SELECT LEFT(content, 300) FROM document_chunks_v4 LIMIT 5;
   -- Verificar metadata JSONB
   SELECT metadata FROM document_chunks_v4 LIMIT 1;
   -- Verificar dimension del embedding
   SELECT array_length(embedding::real[], 1) FROM document_chunks_v4 LIMIT 1;
   ```

## Como anadir una nueva version

1. Crear una nueva migracion Alembic que anada `document_chunks_vN` con el mismo esquema
2. Modificar la logica de chunking/embedding segun sea necesario
3. Anadir la entrada de la version en este fichero
4. Configurar `CHUNKS_TABLE_VERSION=vN` y ejecutar `make ingest`
