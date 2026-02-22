# Multi-stage Dockerfile for PresentLM with CUDA support for Qwen TTS
# Supports both CPU and GPU modes

# Stage 1: Base image with CUDA support
FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04 AS base

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    CUDA_HOME=/usr/local/cuda \
    PATH=/usr/local/cuda/bin:$PATH \
    LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3-dev \
    build-essential \
    git \
    wget \
    curl \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Stage 2: Python dependencies
FROM base AS dependencies

# Upgrade pip and install build tools
RUN pip3 install --upgrade pip setuptools wheel

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
# Install PyTorch with CUDA 12.1 support first
RUN pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install other requirements
RUN pip3 install -r requirements.txt

# Install additional dependencies for Qwen TTS
RUN pip3 install \
    transformers>=4.37.0 \
    accelerate>=0.26.0 \
    scipy>=1.11.0 \
    soundfile>=0.12.0 \
    librosa>=0.10.0

# Stage 3: Application
FROM dependencies AS app

# Copy application code
COPY . /app

# Create necessary directories
RUN mkdir -p /app/data/slides \
    /app/data/audio \
    /app/data/narrations \
    /app/.cache/huggingface

# Set Hugging Face cache directory
ENV HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Check if CUDA is available\n\
if nvidia-smi &> /dev/null; then\n\
    echo "✅ CUDA is available"\n\
    nvidia-smi\n\
else\n\
    echo "⚠️  CUDA not available, running in CPU mode"\n\
fi\n\
\n\
# Check if .env file exists\n\
if [ ! -f /app/.env ]; then\n\
    echo "⚠️  .env file not found, creating from .env.example"\n\
    if [ -f /app/.env.example ]; then\n\
        cp /app/.env.example /app/.env\n\
    fi\n\
fi\n\
\n\
# Run the Streamlit app\n\
echo "🚀 Starting PresentLM..."\n\
streamlit run src/ui/app.py --server.port=8501 --server.address=0.0.0.0\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]

