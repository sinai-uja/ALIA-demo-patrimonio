#!/usr/bin/env bash
# Download ALIA-40b-instruct-2601 Q4_K_M GGUF to backend/models/ALIA-40b-instruct-2601-GGUF/
# This is the single-file GGUF pre-quantized version for Cloud Run with llama.cpp.
#
# Source: https://huggingface.co/mradermacher/ALIA-40b-instruct-2601-GGUF
# File:   ALIA-40b-instruct-2601.Q4_K_M.gguf  (~24.7 GB)
#
# To use a different quantization (e.g. Q5_K_M, Q6_K), override:
#   GGUF_FILE=ALIA-40b-instruct-2601.Q5_K_M.gguf bash scripts/download_alia_gguf.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_DIR="${SCRIPT_DIR}/../models/ALIA-40b-instruct-2601-GGUF"
HF_REPO="mradermacher/ALIA-40b-instruct-2601-GGUF"
GGUF_FILE="${GGUF_FILE:-ALIA-40b-instruct-2601.Q4_K_M.gguf}"

if [ -f "$MODEL_DIR/$GGUF_FILE" ]; then
    echo "Model already exists at $MODEL_DIR/$GGUF_FILE"
    exit 0
fi

mkdir -p "$MODEL_DIR"

echo "Downloading $HF_REPO/$GGUF_FILE via huggingface_hub (~24.7 GB for Q4_K_M)..."
uv run python -c "from huggingface_hub import hf_hub_download; hf_hub_download('$HF_REPO', '$GGUF_FILE', local_dir='$MODEL_DIR')"

echo "Model downloaded to $MODEL_DIR/$GGUF_FILE"
