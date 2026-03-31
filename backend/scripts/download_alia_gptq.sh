#!/usr/bin/env bash
# Download agustim/ALIA-40b-GPTQ-INT4 model to backend/models/ALIA-40b-GPTQ-INT4/
# This is the GPTQ pre-quantized version for Cloud Run (A100 40GB).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_DIR="${SCRIPT_DIR}/../models/ALIA-40b-GPTQ-INT4"

if [ -d "$MODEL_DIR" ] && [ -f "$MODEL_DIR/config.json" ]; then
    echo "Model already exists at $MODEL_DIR"
    exit 0
fi

mkdir -p "$MODEL_DIR"

echo "Downloading agustim/ALIA-40b-GPTQ-INT4 via huggingface_hub (~27GB)..."
uv run python -c "from huggingface_hub import snapshot_download; snapshot_download('agustim/ALIA-40b-GPTQ-INT4', local_dir='$MODEL_DIR')"

echo "Model downloaded to $MODEL_DIR"
