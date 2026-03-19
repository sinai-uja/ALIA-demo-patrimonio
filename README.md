# IAPH Heritage RAG

Conversational AI assistant for the **Instituto Andaluz de Patrimonio Histórico (IAPH)**, commissioned by the **Universidad de Jaén**. Users can explore Andalusian cultural heritage through natural language, generate personalized virtual routes, and access simplified (Lectura Fácil) versions of heritage texts.

## Monorepo structure

```
/
├── backend/          # FastAPI API — hexagonal architecture, Python 3.11, uv
│   ├── src/          # 7 bounded contexts: documents, rag, chat, routes, heritage, search, accessibility
│   ├── docker/       # docker-compose.yml + service Dockerfiles
│   └── alembic/      # DB migrations
├── frontend/         # Next.js 15 web application
└── Guia_Digital_IAPH/  # IAPH parquet data — not committed
```

## Use cases

| Use case | Description |
|----------|-------------|
| **Chatbot patrimonial** | Multi-turn RAG conversation over the full IAPH corpus (134,000+ heritage records) |
| **Rutas virtuales** | Generate personalized routes via smart search with entity detection, LLM query extraction, and multi-filter RAG; interactive per-route guide |
| **Lectura Fácil** | Simplify heritage texts for cognitive accessibility (ILSMH guidelines) |

## AI models

| Role | Model | Notes |
|------|-------|-------|
| Encoder | `BSC-LT/MrBERT` | 308M params · 768-dim · 8,192 token context · mean pooling · Apache 2.0 |
| Decoder | `BSC-LT/salamandra-7b-instruct` | Spanish-capable LLM · served via vLLM |

## Infrastructure

| Service | Image | Port |
|---------|-------|------|
| PostgreSQL + pgvector | `pgvector/pgvector:pg16` | 5432 |
| Embedding service | custom (MrBERT + FastAPI) | 8001 |
| LLM service | `vllm/vllm-openai` *(profile: `llm`)* | 8000 |
| Backend API | custom (FastAPI) | 8080 |

## Quick start

```bash
# 1. Configure environment
cp backend/.env.example backend/.env

# 2. Start infrastructure
docker compose -f backend/docker/docker-compose.yml up -d

# 3. Apply DB migrations
cd backend && uv run alembic upgrade head

# 4. Start backend (dev)
uv run fastapi dev src/main.py          # → http://localhost:8080/api/v1/docs

# 5. Ingest IAPH data (run once per heritage type)
curl -X POST http://localhost:8080/api/v1/documents/ingest \
  -H "Content-Type: application/json" \
  -d '{"source_path": "../Guia_Digital_IAPH", "heritage_type": "PATRIMONIO_INMUEBLE"}'

# 6. Start frontend
cd ../frontend && npm install && npm run dev   # → http://localhost:3000

# Optional: start LLM service (requires NVIDIA GPU)
docker compose -f backend/docker/docker-compose.yml --profile llm up -d
```

Heritage types for ingestion: `PAISAJE_CULTURAL` · `PATRIMONIO_INMATERIAL` · `PATRIMONIO_INMUEBLE` · `PATRIMONIO_MUEBLE`

```bash
# 7. Load heritage assets from IAPH API data (run once)
cd backend && make load-assets     # from ZIP file (data/API_IAPH.zip)
# or: make fetch-assets            # fetch live from IAPH API (requires IAPH_API_TOKEN)
```

## Development

```bash
# Backend tests
cd backend && uv run pytest src/tests/ -v     # 33 tests

# Lint
cd backend && uv run ruff check src/

# New migration after model changes
cd backend && uv run alembic revision --autogenerate -m "description"
```

## Tech stack

**Backend** — Python 3.11 · FastAPI · SQLAlchemy async · pgvector · Alembic · uv · httpx
**Frontend** — Next.js 15 · TypeScript · Tailwind CSS · Zustand · react-leaflet
**Infrastructure** — Docker Compose · PostgreSQL 16 · vLLM

## Sub-READMEs

- [backend/README.md](backend/README.md) — API reference, hexagonal architecture, migration guide
- [frontend/README.md](frontend/README.md) — pages, components, API client
