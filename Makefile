.PHONY: dev backend frontend infra infra-down migrate test lint help

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "  dev        Start backend (infra + API) and frontend concurrently"
	@echo "  backend    Start backend infra services + FastAPI dev server"
	@echo "  frontend   Start Next.js dev server"
	@echo "  infra      Start Docker infra only (postgres + embedding service)"
	@echo "  infra-llm  Start all Docker services including LLM (requires GPU)"
	@echo "  infra-down Stop all Docker services"
	@echo "  migrate    Apply pending Alembic migrations"
	@echo "  test       Run backend test suite"
	@echo "  lint       Run ruff linter on backend"

dev:
	$(MAKE) -C backend infra
	$(MAKE) -j2 _backend-api _frontend

_backend-api:
	$(MAKE) -C backend dev

_frontend:
	$(MAKE) -C frontend dev

backend:
	$(MAKE) -C backend dev

frontend:
	$(MAKE) -C frontend dev

infra:
	$(MAKE) -C backend infra

infra-llm:
	$(MAKE) -C backend infra-llm

infra-down:
	$(MAKE) -C backend infra-down

migrate:
	$(MAKE) -C backend migrate

test:
	$(MAKE) -C backend test

lint:
	$(MAKE) -C backend lint
