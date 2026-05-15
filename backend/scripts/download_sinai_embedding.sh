#!/usr/bin/env bash
# Download SINAI/ALIA-MrBERT-es-cultural-embeddings model to backend/models/
#
# The HuggingFace repo publishes weights under a nested `final_model/` subdirectory.
# This script flattens that layout so the result matches the convention used by the
# other models (MrBERT, Qwen3): config.json + model.safetensors at the root.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_DIR="${SCRIPT_DIR}/../models/ALIA-MrBERT-es-cultural-embeddings"

if [ -d "$MODEL_DIR" ] && [ -f "$MODEL_DIR/config.json" ]; then
    echo "Model already exists at $MODEL_DIR"
    exit 0
fi

mkdir -p "$MODEL_DIR"

echo "Downloading SINAI/ALIA-MrBERT-es-cultural-embeddings via huggingface_hub..."
uv run python -c "from huggingface_hub import snapshot_download; snapshot_download('SINAI/ALIA-MrBERT-es-cultural-embeddings', local_dir='$MODEL_DIR')"

# Flatten nested `final_model/` layout if present
if [ -d "$MODEL_DIR/final_model" ]; then
    echo "Flattening nested final_model/ subdirectory..."
    # Move regular files and hidden files (e.g. .gitattributes), tolerate empty matches
    find "$MODEL_DIR/final_model" -mindepth 1 -maxdepth 1 -exec mv {} "$MODEL_DIR/" \;
    rmdir "$MODEL_DIR/final_model"
fi

echo "Model downloaded to $MODEL_DIR"
