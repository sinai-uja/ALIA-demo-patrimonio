# IAPH Heritage RAG

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=FastAPI&logoColor=white)
![Next JS](https://img.shields.io/badge/Next-black?style=for-the-badge&logo=next.js&logoColor=white)
![TypeScript](https://img.shields.io/badge/typescript-%23007ACC.svg?style=for-the-badge&logo=typescript&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/tailwindcss-%2338B2AC.svg?style=for-the-badge&logo=tailwind-css&logoColor=white)
![Postgres](https://img.shields.io/badge/postgres-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![Swagger](https://img.shields.io/badge/-Swagger-%23Clojure?style=for-the-badge&logo=swagger&logoColor=white)
![Google Cloud](https://img.shields.io/badge/GoogleCloud-%234285F4.svg?style=for-the-badge&logo=google-cloud&logoColor=white)

Conversational AI assistant for the **Instituto Andaluz de Patrimonio Histórico (IAPH)**, commissioned by the **Universidad de Jaen**. Users can explore Andalusian cultural heritage through natural language, generate personalized virtual routes, perform semantic search over heritage assets, and access simplified (Lectura Facil) versions of heritage texts.

## Project partners

<p align="center">
  <a href="https://sinai.ujaen.es/"><img src="frontend/public/images/sinai.png" alt="Departamento SINAI - Universidad de Jaén" height="50"></a>
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <a href="https://alia.gob.es/"><img src="frontend/public/images/alia.png" alt="Proyecto ALIA" height="50"></a>
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <a href="https://www.innovasur.com/"><img src="frontend/public/images/innovasur.png" alt="Innovasur" height="38"></a>
</p>

## Monorepo structure

```
/
├── backend/              # FastAPI API -- hexagonal architecture, Python 3.11, uv
│   ├── src/              # 7 bounded contexts: documents, rag, chat, routes, heritage, search, accessibility
│   ├── docker/           # Backend Dockerfile
│   └── alembic/          # DB migrations
├── frontend/             # Next.js 16 web application
│   └── docker/           # Frontend Dockerfile
├── embedding/            # Embedding service (FastAPI + MrBERT / Qwen3)
├── llm/                  # LLM inference service (vLLM + bitsandbytes quantization)
├── data/                 # IAPH parquet data -- not committed
├── docker-compose.yml          # Full-stack service definitions
├── docker-compose.override.yml # Dev port exposure for local development
├── .env.example                # Environment configuration template
├── .gitlab-ci.yml              # CI/CD pipeline
├── Makefile                    # Root development commands
└── VERSION                     # Semantic version (current: 0.1.5)
```

## Use cases

| Use case | Description |
|----------|-------------|
| **Chatbot patrimonial** | Multi-turn RAG conversation over the full IAPH corpus (134,000+ heritage records) with intent classification and query reformulation |
| **Busqueda semantica** | Faceted semantic search over heritage assets with filtering by province, municipality, heritage type, and more |
| **Rutas virtuales** | Generate personalized routes via smart search with entity detection, LLM query extraction, multi-filter RAG, per-stop structured JSON narrative, heritage asset enrichment (images/coordinates), and interactive per-route guide |
| **Lectura Facil** | Simplify heritage texts for cognitive accessibility (ILSMH guidelines) |

## AI models

| Role | Model | Notes |
|------|-------|-------|
| Encoder (default) | `BSC-LT/MrBERT` | 308M params, 768-dim, 8,192 token context, mean pooling, Apache 2.0 |
| Encoder (alt.) | `Qwen/Qwen3-Embedding-0.6B` | 600M params, 1,024-dim, 32K token context, last-token pooling |
| Decoder (default) | `BSC-LT/salamandra-7b-instruct` | 7B params, Spanish-capable LLM, served via vLLM, 16 GB VRAM min |
| Decoder (large) | `BSC-LT/ALIA-40b-instruct-2601` | 40.4B params, 163K token context, bitsandbytes 4-bit quantization, 32 GB VRAM min |
| Decoder (cloud) | Gemini (`gemini-3.1-flash-lite-preview`) | Cloud LLM backend, selectable via `LLM_PROVIDER=gemini` |

Both encoder models are self-hosted. Decoders are served via **vLLM** from the `llm/` directory (custom Docker image with bitsandbytes support). The Gemini backend is available as a lightweight alternative without GPU requirements.

## Infrastructure

| Service | Image | Internal port | Exposed (host) port |
|---------|-------|:---:|:---:|
| PostgreSQL + pgvector | `pgvector/pgvector:pg16` | 5432 | 15432 |
| Embedding service | custom (MrBERT / Qwen3 + FastAPI) | 8001 | 18001 |
| LLM service | custom vLLM *(profile: `llm`)* | 8000 | 18000 |
| Backend API | custom (FastAPI) | 8080 | 18080 |
| Frontend | custom (Next.js standalone) | 3000 | 3000 |

> Host ports for postgres, embedding, and LLM are exposed via `docker-compose.override.yml` for local development. The API and frontend expose their host ports directly in the main compose file.
>
> The LLM service uses Docker Compose profile `llm` and is not started by default -- use `make infra-llm` when generation endpoints are needed.

## Quick start

```bash
# 1. Configure environment
cp .env.example .env          # edit .env as needed (DB creds, API keys, model config)

# 2. Start infrastructure (postgres + embedding service)
make infra

# 3. Apply DB migrations
make migrate

# 4. Start backend + frontend (dev mode, hot-reload)
make dev                      # API -> http://localhost:18080/api/v1/docs
                              # Frontend -> http://localhost:3000

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

# Database backup
make db-export                 # export database (uses local pg_dump or Docker fallback)
make db-import FILE=path.sql   # import database dump (uses local psql or Docker fallback)

# Docker image management
make build-all REGISTRY=...    # build all Docker images (backend, frontend, embedding, llm)
make push-all REGISTRY=...     # push all Docker images
make build-llm                 # build LLM service image only
make push-llm                  # push LLM service image only

# Cloud Run -- LLM service (ALIA-40b)
make cloud-llm-setup           # first-time LLM infra setup + deploy
make cloud-llm-deploy          # rebuild and redeploy
make cloud-llm-deploy-baked    # rebuild with model baked into image
```

Backend-specific commands (run from `backend/`):

```bash
make ingest                          # ingest parquet data
make reingest                        # delete all chunks and re-ingest from scratch
make load-assets                     # load heritage assets from ZIP
make fetch-assets                    # fetch IAPH API data live (requires IAPH_API_TOKEN)
make migrate-new MSG="description"   # generate new Alembic migration
make download-qwen3                  # download Qwen3 model
make dev-only                        # start FastAPI without infra (assumes infra running)
```

Frontend commands (run from `frontend/`):

```bash
npm run dev    # Next.js dev server (port 3000)
npm run build  # production build
npm run lint   # ESLint
```

## Docker

Two development modes are supported:

| Mode | Command | Description |
|------|---------|-------------|
| **Local dev** | `make dev` | Infra in Docker (with override ports), backend + frontend run natively with hot-reload |
| **Full Docker** | `make docker-up` | Everything containerized, suitable for staging/production |
| **Full Docker + LLM** | `make docker-up-llm` | Adds vLLM service (requires NVIDIA GPU) |

The `docker-compose.override.yml` file exposes internal service ports to the host so that locally-run backend/frontend can reach postgres and the embedding service. Remove or rename this file in production.

## Environment variables

Copy `.env.example` to `.env` at the repo root (or `backend/config/.env.example` to `backend/config/.env`). Key variables:

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://uja:uja@localhost:5432/uja_iaph` | Use port 15432 when running locally against Docker |
| `EMBEDDING_SERVICE_URL` | `http://localhost:8001` | Embedding service endpoint |
| `EMBEDDING_DIM` | `768` | 768 for MrBERT, 1024 for Qwen3 |
| `EMBEDDING_MODEL_DIR` | `MrBERT` | Model directory under `backend/models/` |
| `POOLING_STRATEGY` | `mean` | `mean` (MrBERT) or `last_token` (Qwen3) |
| `LLM_PROVIDER` | `gemini` | LLM backend: `vllm` or `gemini` |
| `LLM_SERVICE_URL` | `http://localhost:8000/v1` | vLLM OpenAI-compatible endpoint |
| `LLM_MODEL_NAME` | `BSC-LT/salamandra-7b-instruct` | Or `BSC-LT/ALIA-40b-instruct-2601` |
| `GEMINI_API_KEY` | *(empty)* | Required when `LLM_PROVIDER=gemini` |
| `RAG_TOP_K` | `5` | Chunks retrieved per query |

## Tech stack

**Backend** -- Python 3.11, FastAPI, SQLAlchemy async, pgvector, Alembic, uv, httpx
**Frontend** -- Next.js 16, TypeScript, Tailwind CSS v4, Zustand, react-leaflet (standalone output for Docker)
**Infrastructure** -- Docker Compose, PostgreSQL 16 + pgvector, vLLM (with bitsandbytes), GitLab CI/CD

## Sub-READMEs

- [backend/README.md](backend/README.md) -- API reference, hexagonal architecture, migration guide
- [frontend/README.md](frontend/README.md) -- pages, components, API client

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
