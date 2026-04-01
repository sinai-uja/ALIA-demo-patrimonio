# =============================================================================
# LLM Service — vLLM with bitsandbytes quantization support
#
# Build context: llm/
# Base: vllm/vllm-openai (OpenAI-compatible API)
#
# Serves LLM inference via the OpenAI-compatible chat/completions API.
# Supports bitsandbytes 4-bit quantization for large models (e.g. ALIA-40b).
#
# Models are downloaded from HuggingFace at first start and cached in a
# Docker volume (hf_cache). For production, use Dockerfile.baked to bake
# the model into the image for faster cold starts.
#
# Configurable via vLLM CLI flags (passed as Docker CMD):
#   --model               — HuggingFace model ID
#   --quantization        — quantization method (bitsandbytes, awq, gptq, etc.)
#   --load-format         — how to load weights (bitsandbytes for on-the-fly quant)
#   --max-model-len       — maximum context length
#   --gpu-memory-utilization — fraction of GPU memory to use (0.0–1.0)
#   --api-key             — API key for Bearer auth (optional)
# =============================================================================

FROM vllm/vllm-openai:v0.18.1

# bitsandbytes enables 4-bit/8-bit quantization at load time,
# allowing 40B+ models to fit on a single 32-40GB GPU.
RUN pip install --no-cache-dir bitsandbytes>=0.45
