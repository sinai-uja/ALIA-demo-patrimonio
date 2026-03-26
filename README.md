# IAPH Heritage RAG

Conversational AI assistant for the **Instituto Andaluz de Patrimonio Histórico (IAPH)**, commissioned by the **Universidad de Jaen**. Users can explore Andalusian cultural heritage through natural language, generate personalized virtual routes, and access simplified (Lectura Facil) versions of heritage texts.

## Monorepo structure

```
/
├── backend/            # FastAPI API — hexagonal architecture, Python 3.11, uv
│   ├── src/            # 7 bounded contexts: documents, rag, chat, routes, heritage, search, accessibility
│   ├── docker/         # Backend Dockerfile
│   └── alembic/        # DB migrations
├── frontend/           # Next.js 16 web application
│   └── docker/         # Frontend Dockerfile
├── embedding/          # Embedding service (FastAPI + MrBERT / Qwen3)
├── data/               # IAPH parquet data — not committed
├── docker-compose.yml          # Full-stack service definitions
├── docker-compose.override.yml # Dev port exposure for local development
├── .env.example                # Environment configuration template
├── .gitlab-ci.yml              # CI/CD pipeline
├── Makefile                    # Root development commands
└── VERSION                     # Semantic version (current: 0.1.0)
```

## Use cases

| Use case | Description |
|----------|-------------|
| **Chatbot patrimonial** | Multi-turn RAG conversation over the full IAPH corpus (134,000+ heritage records) |
| **Rutas virtuales** | Generate personalized routes via smart search with entity detection, LLM query extraction, and multi-filter RAG; interactive per-route guide |
| **Lectura Facil** | Simplify heritage texts for cognitive accessibility (ILSMH guidelines) |

## AI models

| Role | Model | Notes |
|------|-------|-------|
| Encoder (default) | `BSC-LT/MrBERT` | 308M params, 768-dim, 8,192 token context, mean pooling, Apache 2.0 |
| Encoder (alt.) | `Qwen/Qwen3-Embedding-0.6B` | 600M params, 1,024-dim, 32K token context, last-token pooling |
| Decoder (default) | `BSC-LT/salamandra-7b-instruct` | Spanish-capable LLM, served via vLLM (requires GPU) |
| Decoder (alt.) | Gemini (`gemini-3.1-flash-lite-preview`) | Cloud LLM backend, selectable via `LLM_PROVIDER=gemini` |

## Infrastructure

| Service | Image | Internal port | Exposed (host) port |
|---------|-------|:---:|:---:|
| PostgreSQL + pgvector | `pgvector/pgvector:pg16` | 5432 | 15432 |
| Embedding service | custom (MrBERT / Qwen3 + FastAPI) | 8001 | 18001 |
| LLM service | `vllm/vllm-openai` *(profile: `llm`)* | 8000 | 18000 |
| Backend API | custom (FastAPI) | 8080 | 18080 |
| Frontend | custom (Next.js standalone) | 3000 | 3000 |

> Host ports for postgres, embedding, and LLM are exposed via `docker-compose.override.yml` for local development. The API and frontend expose their host ports directly in the main compose file.

## Quick start

```bash
# 1. Configure environment
cp .env.example .env          # edit .env as needed (DB creds, API keys, model config)

# 2. Start infrastructure (postgres + embedding service)
make infra

# 3. Apply DB migrations
make migrate

# 4. Start backend + frontend (dev mode, hot-reload)
make dev                      # API → http://localhost:18080/api/v1/docs
                              # Frontend → http://localhost:3000

# 5. Ingest IAPH data (run once)
cd backend && make ingest     # loads all 4 parquet datasets from data/

# 6. Load heritage assets (run once)
cd backend && make load-assets

# Optional: start LLM service (requires NVIDIA GPU)
make infra-llm
```

For full Docker deployment (everything containerized):

```bash
make docker-up                # or: docker compose up -d --build
make docker-up-llm            # includes LLM service (requires GPU)
```

## Development

All common tasks are available through the root `Makefile`:

```bash
make dev                       # start infra + API + frontend concurrently
make backend                   # start infra + FastAPI only
make frontend                  # start Next.js only
make infra                     # start postgres + embedding service
make infra-llm                 # start all services including LLM
make infra-down                # stop Docker services
make migrate                   # apply pending Alembic migrations
make test                      # run backend test suite
make lint                      # run ruff linter on backend

# Docker image management
make build-all REGISTRY=...    # build all Docker images
make push-all REGISTRY=...     # push all Docker images

# Backend-specific (run from backend/)
cd backend && make ingest                        # ingest parquet data
cd backend && make load-assets                   # load heritage assets from ZIP
cd backend && make migrate-new MSG="description" # generate new Alembic migration
cd backend && make download-qwen3                # download Qwen3 model
```

## Docker

Two development modes are supported:

| Mode | Command | Description |
|------|---------|-------------|
| **Local dev** | `make dev` | Infra in Docker (with override ports), backend + frontend run natively with hot-reload |
| **Full Docker** | `make docker-up` | Everything containerized, suitable for staging/production |
| **Full Docker + LLM** | `make docker-up-llm` | Adds vLLM service (requires NVIDIA GPU) |

The `docker-compose.override.yml` file exposes internal service ports to the host so that locally-run backend/frontend can reach postgres and the embedding service. Remove or rename this file in production.

## Tech stack

**Backend** -- Python 3.11, FastAPI, SQLAlchemy async, pgvector, Alembic, uv, httpx
**Frontend** -- Next.js 16, TypeScript, Tailwind CSS, Zustand, react-leaflet (standalone output for Docker)
**Infrastructure** -- Docker Compose, PostgreSQL 16, vLLM, GitLab CI/CD

## Sub-READMEs

- [backend/README.md](backend/README.md) -- API reference, hexagonal architecture, migration guide
- [frontend/README.md](frontend/README.md) -- pages, components, API client

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
