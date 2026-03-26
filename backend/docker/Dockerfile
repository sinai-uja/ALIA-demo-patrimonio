FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for asyncpg and general build needs
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies (no dev group in production)
RUN uv sync --frozen --no-dev

# Copy application source
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini* ./

EXPOSE 8080

CMD ["uv", "run", "fastapi", "run", "src/main.py", "--host", "0.0.0.0", "--port", "8080"]
