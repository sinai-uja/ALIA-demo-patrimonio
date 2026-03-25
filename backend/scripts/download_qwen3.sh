#!/usr/bin/env bash
# Download Qwen/Qwen3-Embedding-0.6B model to backend/models/Qwen3-Embedding-0.6B/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_DIR="${SCRIPT_DIR}/../models/Qwen3-Embedding-0.6B"

if [ -d "$MODEL_DIR" ] && [ -f "$MODEL_DIR/config.json" ]; then
    echo "Model already exists at $MODEL_DIR"
    exit 0
fi

mkdir -p "$MODEL_DIR"

echo "Downloading Qwen/Qwen3-Embedding-0.6B via huggingface_hub..."
uv run python -c "from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen3-Embedding-0.6B', local_dir='$MODEL_DIR')"

echo "Model downloaded to $MODEL_DIR"
