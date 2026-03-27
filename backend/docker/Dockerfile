# =============================================================================
# Backend API — FastAPI + uv
#
# Build context: backend/
# Image: python:3.11-slim
#
# Serves the FastAPI application (hexagonal architecture) with asyncpg for
# PostgreSQL/pgvector and Alembic for database migrations.
# =============================================================================

FROM python:3.11-slim

WORKDIR /app

# System dependencies:
#   - gcc, libpq-dev: required to compile asyncpg (PostgreSQL async driver)
#   - curl: health checks
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager) from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency manifests first to maximise Docker layer caching —
# dependencies are only reinstalled when pyproject.toml or uv.lock change
COPY pyproject.toml uv.lock ./

# Install production dependencies only (skip dev group: pytest, ruff, etc.)
RUN uv sync --frozen --no-dev

# Copy application source, migration files, and analysis scripts
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini* ./
COPY scripts/ ./scripts/

ENV PORT=20000
EXPOSE ${PORT}

# Production server (fastapi run = uvicorn with auto-workers)
CMD uv run fastapi run src/main.py --host 0.0.0.0 --port ${PORT}
