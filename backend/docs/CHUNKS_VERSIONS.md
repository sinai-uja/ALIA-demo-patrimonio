# Versionado de Document Chunks

La tabla `document_chunks` utiliza un esquema de versionado (`document_chunks_v1`, `document_chunks_v2`, etc.) para que distintas estrategias de chunking coexistan en la base de datos sin perdida de datos.

## Tabla resumen

| Version | Tabla | Estrategia de chunking | Contenido del embedding | Tamano chunk | Overlap | Registros |
|---------|-------|------------------------|-------------------------|--------------|---------|-----------|
| v1 | `document_chunks_v1` | Ventana fija por palabras | Solo texto del chunk | 512 palabras | 64 | ~149,290 |
| v2 | `document_chunks_v2` | Por parrafos (respeta `\n\n`) | Metadata + texto del chunk | 1024 palabras | 128 | Pendiente de ingesta |

## Como cambiar de version

Configurar la variable de entorno `CHUNKS_TABLE_VERSION` en `backend/config/.env`:

```bash
# Usar v1 (chunking original)
CHUNKS_TABLE_VERSION=v1

# Usar v2 (chunking por parrafos + embeddings enriquecidos con metadata)
CHUNKS_TABLE_VERSION=v2
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

## Como anadir una nueva version

1. Crear una nueva migracion Alembic que anada `document_chunks_vN` con el mismo esquema
2. Modificar la logica de chunking/embedding segun sea necesario
3. Anadir la entrada de la version en este fichero
4. Configurar `CHUNKS_TABLE_VERSION=vN` y ejecutar `make ingest`
