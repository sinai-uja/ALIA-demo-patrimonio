FROM nvidia/cuda:12.8.0-runtime-ubuntu22.04

WORKDIR /app

# Install Python 3.11 + system deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3.11 python3.11-venv python3-pip curl && \
    ln -sf /usr/bin/python3.11 /usr/local/bin/python && \
    rm -rf /var/lib/apt/lists/*

# Install PyTorch with CUDA 12.8 (required for Blackwell / RTX 5090)
COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/nightly/cu128 && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code (model is mounted at runtime, NOT copied)
COPY main.py .

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
