@echo off
REM Quick start script for PresentLM Docker on Windows

echo ========================================
echo PresentLM Docker Quick Start (Windows)
echo ========================================
echo.

REM Check if .env exists
if not exist .env (
    echo WARNING: .env file not found
    if exist .env.example (
        echo Creating .env from .env.example...
        copy .env.example .env
        echo SUCCESS: Created .env file
        echo WARNING: Please edit .env and add your API keys!
        echo.
        pause
    ) else (
        echo ERROR: .env.example not found!
        exit /b 1
    )
)

REM Check for Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not installed!
    echo Please install Docker Desktop: https://docs.docker.com/desktop/install/windows-install/
    pause
    exit /b 1
)

REM Check for Docker Compose
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker Compose is not installed!
    echo Docker Compose should be included with Docker Desktop
    pause
    exit /b 1
)

echo.
echo Checking for GPU...
nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo INFO: No GPU detected, running in CPU mode
    set GPU_MODE=false
) else (
    echo SUCCESS: NVIDIA GPU detected
    nvidia-smi --query-gpu=name --format=csv,noheader

    REM Check NVIDIA Docker runtime
    docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi >nul 2>&1
    if errorlevel 1 (
        echo WARNING: NVIDIA Docker runtime not configured
        echo Install NVIDIA Container Toolkit
        echo.
        set /p CONTINUE="Continue in CPU mode? (y/n): "
        if /i not "%CONTINUE%"=="y" exit /b 1
        set GPU_MODE=false
    ) else (
        echo SUCCESS: NVIDIA Docker runtime is working
        set GPU_MODE=true
    )
)

REM Create cache directories
echo.
echo Creating cache directories...
if not exist cache\huggingface mkdir cache\huggingface
if not exist data\slides mkdir data\slides
if not exist data\audio mkdir data\audio
if not exist data\narrations mkdir data\narrations

REM Build and start
echo.
echo Building Docker image...
if "%GPU_MODE%"=="true" (
    docker-compose build
) else (
    docker build -f Dockerfile.cpu -t presentlm-cpu .
)

echo.
echo Starting PresentLM...
if "%GPU_MODE%"=="true" (
    docker-compose up -d
) else (
    docker run -d ^
        -p 8501:8501 ^
        -v "%cd%\data:/app/data" ^
        -v "%cd%\.env:/app/.env:ro" ^
        -v "%cd%\cache\huggingface:/app/.cache/huggingface" ^
        --name presentlm-cpu ^
        presentlm-cpu
)

echo.
echo SUCCESS: PresentLM is starting...
echo.
echo Waiting for container to be ready...
timeout /t 5 /nobreak >nul

if "%GPU_MODE%"=="true" (
    docker-compose ps
) else (
    docker ps --filter name=presentlm-cpu
)

echo.
echo ========================================
echo View logs with:
if "%GPU_MODE%"=="true" (
    echo    docker-compose logs -f
) else (
    echo    docker logs -f presentlm-cpu
)

echo.
echo Access the app at: http://localhost:8501
echo.
echo Stop with:
if "%GPU_MODE%"=="true" (
    echo    docker-compose down
) else (
    echo    docker stop presentlm-cpu
    echo    docker rm presentlm-cpu
)
echo ========================================
echo.
echo Done! Happy presenting!
echo.
pause

