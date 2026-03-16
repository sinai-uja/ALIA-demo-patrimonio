# IAPH Heritage RAG -- Backend

FastAPI backend for the IAPH Heritage RAG system, commissioned by the Universidad de Jaen. The service powers a conversational AI assistant for the Instituto Andaluz de Patrimonio Historico, providing retrieval-augmented generation over heritage domain data.

Built with **Python 3.11**, managed with **uv**, following **hexagonal architecture (Ports & Adapters)**.

---

## Table of contents

- [Architecture overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Environment variables](#environment-variables)
- [Running the application](#running-the-application)
- [API reference](#api-reference)
- [Tests](#tests)
- [Lint and format](#lint-and-format)
- [Database migrations](#database-migrations)
- [Docker services](#docker-services)
- [Hexagonal architecture rules](#hexagonal-architecture-rules)

---

## Architecture overview

```
src/
├── domain/             # Pure Python domain -- entities, value objects, ports, services
│   ├── documents/      # HeritageType, Document, Chunk; ChunkingService; EmbeddingPort, DocumentRepository
│   ├── rag/            # RAGQuery, RetrievedChunk, RAGResponse; ContextAssemblyService; VectorSearchPort, LLMPort
│   ├── chat/           # ChatSession, Message, MessageRole; ChatRepository, RAGPort
│   ├── routes/         # VirtualRoute, RouteStop, HeritageTypeFilter; RouteBuilderService
│   ├── accessibility/  # SimplifiedText, SimplificationLevel; LLMPort
│   └── heritage/       # HeritageAsset, typed raw_data value objects; HeritageRepository
├── application/        # Use cases and DTOs (no framework dependencies)
├── infrastructure/     # SQLAlchemy ORM, httpx adapters, parquet loader
├── composition/        # Dependency wiring (composition root per bounded context)
├── api/v1/endpoints/   # FastAPI routers, Pydantic schemas, FastAPI deps
├── db/                 # AsyncEngine, AsyncSessionLocal, Base, get_db dependency
├── config.py           # pydantic-settings Settings
├── main.py             # FastAPI app, CORS, router registration
└── tests/              # pytest tests
```

Six bounded contexts: **documents**, **rag**, **chat**, **routes**, **accessibility**, and **heritage**. Each context has its own domain, application, infrastructure, composition, and API layers.

---

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- Docker and Docker Compose (for infrastructure services)
- NVIDIA GPU (optional, required for the embedding service and LLM service)

---

## Installation

```bash
cd backend/
cp .env.example .env      # edit values as needed
uv sync                   # install all dependencies
```

---

## Environment variables

Configuration is loaded from a `.env` file via `pydantic-settings`. See `.env.example` for a complete template.

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://uja:uja@localhost:5432/uja_iaph` | Async PostgreSQL connection URL |
| `EMBEDDING_SERVICE_URL` | `http://localhost:8001` | MrBERT embedding HTTP service URL |
| `EMBEDDING_DIM` | `768` | Embedding vector dimension |
| `LLM_SERVICE_URL` | `http://localhost:8000/v1` | vLLM OpenAI-compatible endpoint URL |
| `LLM_MODEL_NAME` | `BSC-LT/salamandra-7b-instruct` | LLM model identifier |
| `LLM_MAX_TOKENS` | `2048` | Maximum tokens for LLM generation |
| `LLM_TEMPERATURE` | `0.7` | LLM sampling temperature |
| `RAG_TOP_K` | `5` | Number of chunks retrieved per query |
| `RAG_CHUNK_SIZE` | `512` | Words per chunk during ingestion |
| `RAG_CHUNK_OVERLAP` | `64` | Overlap words between consecutive chunks |
| `CHUNKS_TABLE_VERSION` | `v1` | Versioned chunk table suffix (table name: `document_chunks_{version}`) |
| `API_V1_PREFIX` | `/api/v1` | API version prefix |
| `PROJECT_NAME` | `IAPH Heritage RAG` | Project name (shown in OpenAPI docs) |
| `DEBUG` | `false` | Enable debug mode |

---

## Running the application

### Start infrastructure services

```bash
docker compose -f docker/docker-compose.yml up -d
```

### Apply database migrations

```bash
uv run alembic upgrade head
```

### Start the dev server (hot-reload)

```bash
uv run fastapi dev src/main.py
```

The API will be available at `http://localhost:8000` in local dev mode, or `http://localhost:8080` when running inside Docker.

### Start with the LLM service (requires NVIDIA GPU)

```bash
docker compose -f docker/docker-compose.yml --profile llm up -d
```

---

## API reference

All endpoints are prefixed with `/api/v1/`. Interactive Swagger docs are available at `/api/v1/docs`.

### Health check

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Service health check (not under `/api/v1/`) |

### Documents

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/documents/ingest` | Ingest a parquet source into the vector store |
| `GET` | `/documents/chunks/{document_id}` | List chunks for a document |

Heritage types: `PAISAJE_CULTURAL`, `PATRIMONIO_INMATERIAL`, `PATRIMONIO_INMUEBLE`, `PATRIMONIO_MUEBLE`

**Ingest example:**

```bash
curl -X POST http://localhost:8080/api/v1/documents/ingest \
  -H "Content-Type: application/json" \
  -d '{"source_path": "../Guia_Digital_IAPH", "heritage_type": "PATRIMONIO_INMUEBLE", "chunk_size": 512}'
```

### RAG

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/rag/query` | Single-turn RAG query (embed, search, assemble, generate) |

```bash
curl -X POST http://localhost:8080/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Castillos medievales en Jaen", "province_filter": "Jaen", "top_k": 5}'
```

### Chat

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/chat/sessions` | Create a new chat session |
| `GET` | `/chat/sessions` | List all sessions (ordered by most recently updated) |
| `DELETE` | `/chat/sessions/{id}` | Delete a session and all its messages |
| `GET` | `/chat/sessions/{id}/messages` | Get message history for a session |
| `POST` | `/chat/sessions/{id}/messages` | Send a message (triggers RAG pipeline, returns assistant response) |

### Routes

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/routes/generate` | Generate a personalized virtual heritage route |
| `GET` | `/routes` | List generated routes (optional `?province=` filter) |
| `GET` | `/routes/{id}` | Get a specific route |
| `POST` | `/routes/{id}/guide` | Ask the interactive guide a question about a route |

### Accessibility

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/accessibility/simplify` | Simplify text following Lectura Facil guidelines |

Simplification levels: `basic` (ILSMH, maximum simplification) and `intermediate` (accessible for the general public).

### Heritage

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/heritage` | List heritage assets with filters and pagination |
| `GET` | `/heritage/{id}` | Get a single asset with full typed details |

**Query parameters for list:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `heritage_type` | string | Filter: `inmueble`, `mueble`, `inmaterial`, `paisaje` |
| `province` | string | Filter by province |
| `municipality` | string | Filter by municipality |
| `limit` | int | Page size (1-200, default 50) |
| `offset` | int | Offset for pagination |

The detail endpoint returns a `details` object whose shape depends on `heritage_type` (typed as `InmuebleDetails`, `MuebleDetails`, `InmaterialDetails`, or `PaisajeDetails`). The raw JSONB data from the IAPH API is parsed into clean, strongly-typed fields including typologies, images, bibliography, and related assets.

**Data loading:** The `heritage_assets` table is populated from the IAPH API, not from the parquet ingestion pipeline.

```bash
# From backend/
make load-assets     # Load from ZIP file (data/API_IAPH.zip)
make fetch-assets    # Fetch live from IAPH API (requires IAPH_API_TOKEN env var)
```

---

## Tests

```bash
# Run all tests
uv run pytest src/tests/ -v

# Domain unit tests only
uv run pytest src/tests/domain/ -v

# API tests only (with mocks)
uv run pytest src/tests/api/ -v

# Run a single test
uv run pytest src/tests/path/to/test_file.py::test_name -v
```

---

## Lint and format

The project uses [Ruff](https://docs.astral.sh/ruff/) for linting (rules: E, F, I, UP; line length: 100).

```bash
# Check for lint errors
uv run ruff check src/

# Auto-fix lint errors
uv run ruff check src/ --fix
```

---

## Database migrations

Managed with [Alembic](https://alembic.sqlalchemy.org/). Migration scripts live in `alembic/`.

```bash
# Apply all pending migrations
uv run alembic upgrade head

# Generate a new migration from model changes
uv run alembic revision --autogenerate -m "description of change"

# Roll back the last migration
uv run alembic downgrade -1
```

---

## Docker services

Defined in `docker/docker-compose.yml`:

| Service | Image | Port | Notes |
|---------|-------|------|-------|
| `postgres` | `pgvector/pgvector:pg16` | 5432 | PostgreSQL 16 with pgvector extension |
| `embedding-service` | Custom (Dockerfile in `docker/embedding-service/`) | 8001 | MrBERT FastAPI microservice; model mounted from `models/MrBERT/` |
| `llm-service` | `vllm/vllm-openai:latest` | 8000 | vLLM serving salamandra-7b-instruct; profile `llm`, requires NVIDIA GPU |
| `api` | Custom (Dockerfile in `docker/api/`) | 8080 | FastAPI backend; depends on postgres and embedding-service |

---

## Hexagonal architecture rules

1. **Domain** has zero external imports -- no SQLAlchemy, no httpx, no FastAPI. Pure Python only.
2. **Application** imports only from domain. Contains use cases and DTOs.
3. **Infrastructure** implements domain ports (adapters for databases, HTTP clients, etc.).
4. **Composition roots** wire concrete adapters to domain ports. One composition module per bounded context.
5. **API layer** imports composition roots via FastAPI `Depends`. Routers never instantiate adapters directly.
