.PHONY: dev backend frontend infra infra-llm infra-down docker-up docker-up-llm docker-down migrate test lint help

COMPOSE = docker compose

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "  dev           Start backend (infra + API) and frontend concurrently"
	@echo "  backend       Start backend infra services + FastAPI dev server"
	@echo "  frontend      Start Next.js dev server"
	@echo "  infra         Start Docker infra only (postgres + embedding service)"
	@echo "  infra-llm     Start all Docker services including LLM (requires GPU)"
	@echo "  infra-down    Stop all Docker services"
	@echo "  docker-up     Build and start all services (postgres, embedding, api, frontend)"
	@echo "  docker-up-llm Build and start all services including LLM (requires GPU)"
	@echo "  docker-down   Stop all Docker services"
	@echo "  migrate       Apply pending Alembic migrations"
	@echo "  test          Run backend test suite"
	@echo "  lint          Run ruff linter on backend"

dev:
	$(COMPOSE) up -d postgres embedding-service
	$(MAKE) -j2 _backend-api _frontend

_backend-api:
	$(MAKE) -C backend dev-only

_frontend:
	$(MAKE) -C frontend dev

backend:
	$(MAKE) -C backend dev

frontend:
	$(MAKE) -C frontend dev

infra:
	$(COMPOSE) up -d postgres embedding-service

infra-llm:
	$(COMPOSE) --profile llm up -d postgres embedding-service llm-service

infra-down:
	$(COMPOSE) down

docker-up:
	$(COMPOSE) up -d --build

docker-up-llm:
	$(COMPOSE) --profile llm up -d --build

docker-down:
	$(COMPOSE) down

migrate:
	$(MAKE) -C backend migrate

test:
	$(MAKE) -C backend test

lint:
	$(MAKE) -C backend lint
