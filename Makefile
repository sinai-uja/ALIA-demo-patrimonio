.PHONY: dev backend frontend infra infra-db infra-embedding infra-llm infra-down \
       docker-up docker-up-llm docker-down \
       build-backend build-frontend build-embedding build-llm build-all \
       push-backend push-frontend push-embedding push-llm push-all \
       cloud-setup cloud-setup-baked cloud-generate-sa-key cloud-deploy cloud-deploy-baked cloud-deploy-skip-build \
       cloud-llm-setup cloud-llm-setup-model cloud-llm-setup-baked cloud-llm-generate-sa-key \
       cloud-llm-deploy cloud-llm-deploy-baked cloud-llm-deploy-skip-build cloud-llm-deploy-baked-skip-build \
       migrate test lint db-export db-export-docker db-import db-import-docker help

COMPOSE = docker compose
VERSION = $(shell cat VERSION)
REGISTRY ?= gitlab.innovasur.es:5005/uja/iaph-rag-monorepo

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Development:"
	@echo "  dev              Start backend (infra + API) and frontend concurrently"
	@echo "  backend          Start backend infra services + FastAPI dev server"
	@echo "  frontend         Start Next.js dev server"
	@echo "  infra            Start all infra (postgres + embedding + LLM)"
	@echo "  infra-db         Start postgres only"
	@echo "  infra-embedding  Start embedding service only"
	@echo "  infra-llm        Start LLM service only (requires GPU)"
	@echo "  infra-down       Stop all Docker services"
	@echo ""
	@echo "Docker Compose:"
	@echo "  docker-up        Build and start all services"
	@echo "  docker-up-llm    Build and start all services including LLM (requires GPU)"
	@echo "  docker-down      Stop all Docker services"
	@echo ""
	@echo "Docker Build (uses VERSION file, current: $(VERSION)):"
	@echo "  build-backend    Build backend image"
	@echo "  build-frontend   Build frontend image"
	@echo "  build-embedding  Build embedding image"
	@echo "  build-llm        Build LLM service image"
	@echo "  build-all        Build all images"
	@echo ""
	@echo "Docker Push (REGISTRY=<registry>, current: $(REGISTRY)):"
	@echo "  push-backend     Push backend image"
	@echo "  push-frontend    Push frontend image"
	@echo "  push-embedding   Push embedding image"
	@echo "  push-llm         Push LLM service image"
	@echo "  push-all         Push all images"
	@echo ""
	@echo "Cloud Run (embedding service):"
	@echo "  cloud-setup              First-time infra setup + deploy (GCS FUSE)"
	@echo "  cloud-setup-models       Setup + upload models to GCS"
	@echo "  cloud-setup-baked        Setup + bake models into image (fast cold start)"
	@echo "  cloud-generate-sa-key    Generate service account key for external servers"
	@echo "  cloud-deploy             Rebuild and redeploy (GCS FUSE)"
	@echo "  cloud-deploy-baked       Rebuild with models baked in (fast cold start)"
	@echo "  cloud-deploy-skip-build  Redeploy without rebuilding image"
	@echo ""
	@echo "Cloud Run (LLM service — ALIA-40b):"
	@echo "  cloud-llm-setup              First-time LLM infra setup + deploy"
	@echo "  cloud-llm-setup-model        Setup + upload model to GCS"
	@echo "  cloud-llm-setup-baked        Setup + bake model into image"
	@echo "  cloud-llm-generate-sa-key    Generate service account key"
	@echo "  cloud-llm-deploy             Rebuild and redeploy"
	@echo "  cloud-llm-deploy-baked       Rebuild with model baked in"
	@echo "  cloud-llm-deploy-skip-build  Redeploy without rebuilding (GCS FUSE)"
	@echo "  cloud-llm-deploy-baked-skip-build  Redeploy baked image without rebuilding"
	@echo ""
	@echo "Database:"
	@echo "  db-export        Export database (local)"
	@echo "  db-export-docker Export database (Docker container)"
	@echo "  db-import        Import database (local, FILE=path/to/dump)"
	@echo "  db-import-docker Import database (Docker, FILE=path/to/dump)"
	@echo ""
	@echo "Other:"
	@echo "  migrate          Apply pending Alembic migrations"
	@echo "  test             Run backend test suite"
	@echo "  lint             Run ruff linter on backend"

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
	$(COMPOSE) --profile llm up -d postgres embedding-service llm-service

infra-db:
	$(COMPOSE) up -d postgres

infra-embedding:
	$(COMPOSE) up -d embedding-service

infra-llm:
	$(COMPOSE) --profile llm up -d llm-service

infra-down:
	$(COMPOSE) down

docker-up:
	$(COMPOSE) up -d --build

docker-up-llm:
	$(COMPOSE) --profile llm up -d --build

docker-down:
	$(COMPOSE) down

# ---------------------------------------------------------------------------
# Docker Build
# ---------------------------------------------------------------------------

build-backend:
	docker build --tag $(REGISTRY)/backend:$(VERSION) --tag $(REGISTRY)/backend:latest -f backend/docker/Dockerfile backend

build-frontend:
	docker build --tag $(REGISTRY)/frontend:$(VERSION) --tag $(REGISTRY)/frontend:latest -f frontend/docker/Dockerfile frontend

build-embedding:
	docker build --tag $(REGISTRY)/embedding:$(VERSION) --tag $(REGISTRY)/embedding:latest -f embedding/Dockerfile embedding

build-llm:
	docker build --tag $(REGISTRY)/llm:$(VERSION) --tag $(REGISTRY)/llm:latest -f llm/Dockerfile llm

build-all: build-backend build-frontend build-embedding build-llm

# ---------------------------------------------------------------------------
# Docker Push
# ---------------------------------------------------------------------------

push-backend: build-backend
	docker push $(REGISTRY)/backend:$(VERSION)
	docker push $(REGISTRY)/backend:latest

push-frontend: build-frontend
	docker push $(REGISTRY)/frontend:$(VERSION)
	docker push $(REGISTRY)/frontend:latest

push-embedding: build-embedding
	docker push $(REGISTRY)/embedding:$(VERSION)
	docker push $(REGISTRY)/embedding:latest

push-llm: build-llm
	docker push $(REGISTRY)/llm:$(VERSION)
	docker push $(REGISTRY)/llm:latest

push-all: push-backend push-frontend push-embedding push-llm

# ---------------------------------------------------------------------------
# Cloud Run (embedding service)
# ---------------------------------------------------------------------------

cloud-setup:
	./embedding/scripts/setup.sh

cloud-setup-models:
	./embedding/scripts/setup.sh --upload-models

cloud-setup-baked:
	./embedding/scripts/setup.sh --bake-models

cloud-generate-sa-key:
	./embedding/scripts/setup.sh --generate-sa-key

cloud-deploy:
	./embedding/scripts/deploy.sh

cloud-deploy-baked:
	./embedding/scripts/deploy.sh --bake-models

cloud-deploy-skip-build:
	./embedding/scripts/deploy.sh --skip-build

cloud-deploy-baked-skip-build:
	./embedding/scripts/deploy.sh --bake-models --skip-build

# ---------------------------------------------------------------------------
# Cloud Run (LLM service — ALIA-40b)
# ---------------------------------------------------------------------------

cloud-llm-setup:
	./llm/scripts/setup.sh

cloud-llm-setup-model:
	./llm/scripts/setup.sh --upload-model

cloud-llm-setup-baked:
	./llm/scripts/setup.sh --bake-model

cloud-llm-generate-sa-key:
	./llm/scripts/setup.sh --generate-sa-key

cloud-llm-deploy:
	./llm/scripts/deploy.sh

cloud-llm-deploy-baked:
	./llm/scripts/deploy.sh --bake-model

cloud-llm-deploy-skip-build:
	./llm/scripts/deploy.sh --skip-build

cloud-llm-deploy-baked-skip-build:
	./llm/scripts/deploy.sh --bake-model --skip-build

# ---------------------------------------------------------------------------
# Other
# ---------------------------------------------------------------------------

migrate:
	$(MAKE) -C backend migrate

test:
	$(MAKE) -C backend test

lint:
	$(MAKE) -C backend lint

db-export:
	$(MAKE) -C backend db-export

db-export-docker:
	$(MAKE) -C backend db-export-docker

db-import:
	$(MAKE) -C backend db-import FILE=$(FILE)

db-import-docker:
	$(MAKE) -C backend db-import-docker FILE=$(FILE)
