#!/bin/bash
# Quick start script for PresentLM Docker

set -e

echo "🚀 PresentLM Docker Quick Start"
echo "================================"

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found"
    if [ -f .env.example ]; then
        echo "📋 Creating .env from .env.example..."
        cp .env.example .env
        echo "✅ Created .env file"
        echo "⚠️  Please edit .env and add your API keys!"
        echo ""
        read -p "Press Enter to continue after editing .env..."
    else
        echo "❌ .env.example not found!"
        exit 1
    fi
fi

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed!"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check for Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed!"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Check for NVIDIA GPU
echo ""
echo "🔍 Checking for GPU..."
if command -v nvidia-smi &> /dev/null; then
    echo "✅ NVIDIA GPU detected"
    nvidia-smi --query-gpu=name --format=csv,noheader

    # Check for NVIDIA Docker runtime
    if docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
        echo "✅ NVIDIA Docker runtime is working"
        GPU_MODE=true
    else
        echo "⚠️  NVIDIA Docker runtime not found"
        echo "Install it: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
        echo ""
        read -p "Continue in CPU mode? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
        GPU_MODE=false
    fi
else
    echo "ℹ️  No GPU detected, running in CPU mode"
    GPU_MODE=false
fi

# Create cache directory
echo ""
echo "📁 Creating cache directories..."
mkdir -p cache/huggingface
mkdir -p data/slides data/audio data/narrations

# Build and start
echo ""
echo "🔨 Building Docker image..."
if [ "$GPU_MODE" = true ]; then
    docker-compose build
else
    docker build -f Dockerfile.cpu -t presentlm-cpu .
fi

echo ""
echo "🚀 Starting PresentLM..."
if [ "$GPU_MODE" = true ]; then
    docker-compose up -d
else
    docker run -d \
        -p 8501:8501 \
        -v "$(pwd)/data:/app/data" \
        -v "$(pwd)/.env:/app/.env:ro" \
        -v "$(pwd)/cache/huggingface:/app/.cache/huggingface" \
        --name presentlm-cpu \
        presentlm-cpu
fi

echo ""
echo "✅ PresentLM is starting..."
echo ""
echo "📊 Checking status..."
sleep 5

if [ "$GPU_MODE" = true ]; then
    docker-compose ps
else
    docker ps --filter name=presentlm-cpu
fi

echo ""
echo "📝 View logs with:"
if [ "$GPU_MODE" = true ]; then
    echo "   docker-compose logs -f"
else
    echo "   docker logs -f presentlm-cpu"
fi

echo ""
echo "🌐 Access the app at: http://localhost:8501"
echo ""
echo "🛑 Stop with:"
if [ "$GPU_MODE" = true ]; then
    echo "   docker-compose down"
else
    echo "   docker stop presentlm-cpu && docker rm presentlm-cpu"
fi
echo ""
echo "✨ Done! Happy presenting! 🎤"

