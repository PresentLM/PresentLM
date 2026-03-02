#!/bin/bash
# Quick start script for PresentLM Docker (CPU only)

set -e

echo "PresentLM Docker Quick Start (CPU only)"
echo "================================"

# Check if .env exists
if [ ! -f .env ]; then
    echo "WARNING: .env file not found"
    if [ -f .env.example ]; then
        echo "Creating .env from .env.example..."
        cp .env.example .env
        echo "SUCCESS: Created .env file"
        echo "WARNING: Please edit .env and add your API keys!"
        echo ""
        read -p "Press Enter to continue after editing .env..."
    else
        echo "ERROR: .env.example not found!"
        exit 1
    fi
fi

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed!"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check for Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "ERROR: Docker Compose is not installed!"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo ""
echo "Creating cache directories..."
mkdir -p cache/huggingface
mkdir -p data/slides data/audio data/narrations

echo ""
echo "Building Docker image (CPU only)..."
docker-compose build

echo ""
echo "Starting PresentLM (CPU only)..."
docker-compose up -d

echo ""
echo "PresentLM is starting..."
echo ""
echo "Checking status..."
sleep 5
docker-compose ps

echo ""
echo "View logs with:"
echo "   docker-compose logs -f"
echo ""
echo "Access the app at: http://localhost:8501"
echo ""
echo "Stop with:"
echo "   docker-compose down"
echo ""
echo "Done! Happy presenting!"
