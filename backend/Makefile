.PHONY: dev infra infra-llm infra-down migrate migrate-new lint test ingest help

COMPOSE = docker compose -f docker/docker-compose.yml
ENV_FILE = config/.env

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "  dev          Start infra services + FastAPI in dev mode (hot-reload)"
	@echo "  infra        Start postgres + embedding-service"
	@echo "  infra-llm    Start all services including LLM (requires GPU)"
	@echo "  infra-down   Stop all services"
	@echo "  migrate      Apply all pending Alembic migrations"
	@echo "  migrate-new  Generate a new Alembic migration (MSG='description')"
	@echo "  lint         Run ruff check on src/"
	@echo "  test         Run test suite with pytest"
	@echo "  ingest       Ingest all IAPH parquet datasets"

dev: infra
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
