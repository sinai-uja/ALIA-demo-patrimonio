# =============================================================================
# Embedding Service — dual encoder (MrBERT / Qwen3-Embedding-0.6B)
#
# Build context: embedding/
# Image: nvidia/cuda:12.8.0-runtime-ubuntu22.04
#
# Serves a transformer encoder model via HTTP (FastAPI + uvicorn).
# The model files are NOT baked into the image — they are mounted at runtime
# as a read-only volume at /app/model (see docker-compose.yml).
#
# Configurable via environment variables:
#   MODEL_PATH       — path to the mounted model (default: /app/model)
#   DEVICE           — compute device: "cuda" or "cpu" (default: cpu)
#   POOLING_STRATEGY — "mean" (MrBERT) or "last_token" (Qwen3)
#   MAX_LENGTH       — max token length: 8192 (MrBERT) or 32768 (Qwen3)
# =============================================================================

FROM nvidia/cuda:12.8.0-runtime-ubuntu22.04

WORKDIR /app

# Install Python 3.11 and minimal system dependencies
#   - python3.11-venv: required for pip to work in modern Ubuntu
#   - curl: health checks
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3.11 python3.11-venv python3-pip curl && \
    ln -sf /usr/bin/python3.11 /usr/local/bin/python && \
    rm -rf /var/lib/apt/lists/*

# Install PyTorch with CUDA 12.8 support (nightly index for Blackwell / RTX 5090),
# then install the remaining Python dependencies (transformers, fastapi, etc.)
COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/nightly/cu128 && \
    pip install --no-cache-dir -r requirements.txt

# Copy the FastAPI application (single file — model weights are mounted, not copied)
COPY main.py .

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
