@echo off
REM Quick start script for PresentLM Docker on Windows (CPU only)

echo ========================================
echo PresentLM Docker Quick Start (Windows, CPU only)
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
echo Creating cache directories...
if not exist cache\huggingface mkdir cache\huggingface
if not exist data\slides mkdir data\slides
if not exist data\audio mkdir data\audio
if not exist data\narrations mkdir data\narrations

echo.
echo Building Docker image (CPU only)...
docker-compose build

echo.
echo Starting PresentLM (CPU only)...
docker-compose up -d

echo.
echo SUCCESS: PresentLM is starting...
echo.
echo Waiting for container to be ready...
timeout /t 5 /nobreak >nul

docker-compose ps

echo.
echo ========================================
echo View logs with:
echo    docker-compose logs -f
echo.
echo Access the app at: http://localhost:8501
echo.
echo Stop with:
echo    docker-compose down
echo ========================================
echo.
echo Done! Happy presenting!
echo.
pause
