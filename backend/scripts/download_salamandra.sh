#!/usr/bin/env bash
# Download BSC-LT/salamandra-7b-instruct model to backend/models/salamandra-7b-instruct/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_DIR="${SCRIPT_DIR}/../models/salamandra-7b-instruct"

if [ -d "$MODEL_DIR" ] && [ -f "$MODEL_DIR/config.json" ]; then
    echo "Model already exists at $MODEL_DIR"
    exit 0
fi

mkdir -p "$MODEL_DIR"

echo "Downloading BSC-LT/salamandra-7b-instruct via huggingface_hub (~14GB)..."
uv run python -c "from huggingface_hub import snapshot_download; snapshot_download('BSC-LT/salamandra-7b-instruct', local_dir='$MODEL_DIR')"

echo "Model downloaded to $MODEL_DIR"
