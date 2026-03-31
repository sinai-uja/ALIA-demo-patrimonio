.PHONY: dev dev-only infra infra-llm infra-down migrate migrate-new lint test ingest reingest load-assets fetch-assets download-qwen3 download-reranker download-salamandra download-alia-gptq analyze-feedback analyze-queries manage-users db-export db-export-docker db-import db-import-docker help

COMPOSE = docker compose -f ../docker-compose.yml -f ../docker-compose.override.yml
ENV_FILE = config/.env

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "  dev          Start infra services + FastAPI in dev mode (hot-reload)"
	@echo "  dev-only     Start FastAPI in dev mode (without infra)"
	@echo "  infra        Start postgres + embedding-service"
	@echo "  infra-llm    Start all services including LLM (requires GPU)"
	@echo "  infra-down   Stop all services"
	@echo "  migrate      Apply all pending Alembic migrations"
	@echo "  migrate-new  Generate a new Alembic migration (MSG='description')"
	@echo "  lint         Run ruff check on src/"
	@echo "  test         Run test suite with pytest"
	@echo "  ingest       Ingest all IAPH parquet datasets (skips existing chunks)"
	@echo "  reingest     Delete all chunks and re-ingest from scratch"
	@echo "  load-assets  Load IAPH API data from ZIP into heritage_assets"
	@echo "  fetch-assets Fetch IAPH API data live (requires IAPH_API_TOKEN)"
	@echo "  download-qwen3       Download Qwen3-Embedding-0.6B model"
	@echo "  download-reranker    Download Qwen3-Reranker-0.6B model"
	@echo "  download-salamandra  Download salamandra-7b-instruct (~14GB, local dev)"
	@echo "  download-alia-gptq   Download ALIA-40b-GPTQ-INT4 (~27GB, Cloud Run)"
	@echo "  analyze-feedback Analyze feedback logs and generate CSV/JSON reports"
	@echo "  analyze-queries  List all search/route queries with RAG results"
	@echo "  manage-users     Manage users (ARGS='create-user --username x --password y')"
	@echo "  db-export        Export database (local, port 15432)"
	@echo "  db-export-docker Export database (Docker container)"
	@echo "  db-import        Import database (local, FILE=path/to/dump)"
	@echo "  db-import-docker Import database (Docker, FILE=path/to/dump)"

dev: infra
	uv run fastapi dev src/main.py --port 18080

dev-only:
	uv run fastapi dev src/main.py --port 18080

infra:
	$(COMPOSE) up -d postgres embedding-service

infra-llm:
	$(COMPOSE) --profile llm up -d postgres embedding-service llm-service

infra-down:
	$(COMPOSE) down

migrate:
	uv run alembic upgrade head

migrate-new:
	uv run alembic revision --autogenerate -m "$(MSG)"

lint:
	uv run ruff check src/

test:
	uv run pytest src/tests/ -v

ingest:
	uv run python -m scripts.ingest --dataset all

reingest:
	uv run python -m scripts.ingest --dataset all --reingest

load-assets:
	uv run python -m scripts.load_api_assets --source ../data/API_IAPH.zip

fetch-assets:
	uv run python -m scripts.fetch_iaph_api

download-qwen3:
	bash scripts/download_qwen3.sh

download-reranker:
	bash scripts/download_reranker.sh

download-salamandra:
	bash scripts/download_salamandra.sh

download-alia-gptq:
	bash scripts/download_alia_gptq.sh

analyze-feedback:
	uv run python scripts/analyze_feedback.py

analyze-queries:
	uv run python -m scripts.analyze_queries

manage-users:
	uv run python -m scripts.manage_users $(ARGS)

db-export:
	bash scripts/db_backup.sh export

db-export-docker:
	bash scripts/db_backup.sh export --docker

db-import:
	bash scripts/db_backup.sh import $(FILE)

db-import-docker:
	bash scripts/db_backup.sh import --docker $(FILE)
