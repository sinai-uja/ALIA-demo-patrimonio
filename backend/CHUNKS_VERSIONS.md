# Document Chunks Versioning

The `document_chunks` table uses a versioning scheme (`document_chunks_v1`, `document_chunks_v2`, etc.) so that different chunking strategies can coexist in the database without data loss.

## How to switch versions

Set the environment variable `CHUNKS_TABLE_VERSION` in `backend/config/.env`:

```bash
# Use v1 (original chunking)
CHUNKS_TABLE_VERSION=v1

# Use v2 (paragraph-aware chunking + metadata-enriched embeddings)
CHUNKS_TABLE_VERSION=v2
```

Restart the backend after changing the variable. No migration or re-ingestion is needed to switch — both tables coexist.

## Versions

### v1 — Word-boundary chunking (original)

- **Table**: `document_chunks_v1`
- **Chunk strategy**: Fixed word-count windows (512 words, 64 overlap)
- **Embedding content**: Raw chunk text only
- **Records**: ~149,290 chunks from all 4 datasets
- **Created**: Initial ingestion

### v2 — Paragraph-aware chunking + metadata enrichment

- **Table**: `document_chunks_v2`
- **Chunk strategy**: Paragraph-aware splitting (respects `\n\n` boundaries, never cuts mid-paragraph). Fallback to word-level split for oversized paragraphs.
- **Embedding content**: Metadata header prepended before embedding:
  ```
  Titulo: X | Tipo: Y | Provincia: Z | Municipio: W
  ---
  {chunk content}
  ```
- **Recommended config**:
  ```bash
  RAG_CHUNK_SIZE=1024
  RAG_CHUNK_OVERLAP=128
  CHUNKS_TABLE_VERSION=v2
  ```
- **Records**: Empty until `make ingest` is run with `CHUNKS_TABLE_VERSION=v2`

## How to ingest into v2

1. Apply the migration:
   ```bash
   make migrate
   ```

2. Set environment variables in `backend/config/.env`:
   ```bash
   CHUNKS_TABLE_VERSION=v2
   RAG_CHUNK_SIZE=1024
   RAG_CHUNK_OVERLAP=128
   ```

3. Run ingestion:
   ```bash
   cd backend && make ingest
   ```

4. Verify:
   ```sql
   SELECT COUNT(*) FROM document_chunks_v2;
   ```

## How to add a new version

1. Create a new Alembic migration adding `document_chunks_vN` with the same schema
2. Update chunking/embedding logic as needed
3. Add the version entry to this file
4. Set `CHUNKS_TABLE_VERSION=vN` and run `make ingest`
