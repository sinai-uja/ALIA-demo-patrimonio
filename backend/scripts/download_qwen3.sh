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

if command -v huggingface-cli &> /dev/null; then
    echo "Downloading Qwen/Qwen3-Embedding-0.6B via huggingface-cli..."
    huggingface-cli download Qwen/Qwen3-Embedding-0.6B --local-dir "$MODEL_DIR"
elif command -v git &> /dev/null && git lfs version &> /dev/null; then
    echo "Downloading Qwen/Qwen3-Embedding-0.6B via git lfs..."
    git clone https://huggingface.co/Qwen/Qwen3-Embedding-0.6B "$MODEL_DIR"
else
    echo "ERROR: Neither huggingface-cli nor git-lfs found."
    echo "Install one of:"
    echo "  pip install huggingface_hub[cli]"
    echo "  apt install git-lfs && git lfs install"
    exit 1
fi

echo "Model downloaded to $MODEL_DIR"
