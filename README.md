# PresentLM

PresentLM transforms presentations into interactive, narrated experiences with AI-powered question and answer capabilities.

## Features

- AI-generated narration for presentation slides
- Text-to-speech (TTS) using OpenAI or local Qwen TTS
- Interactive Q&A via text or voice
- Auto-play for synchronized audio and slide progression
- Supports PDF and PowerPoint files

---

## Project Structure

- `src/` - Main application source code (UI, core logic, utilities)
- `data/` - Stores generated presentations, audio, narrations, and related metadata
- `scripts/` - Utility scripts (e.g., for plotting benchmarks)
- `PresentLM-doc/` - Documentation site (Docusaurus)
- `Dockerfile`, `Dockerfile.cpu` - Docker build files for different environments
- `docker-compose.yml` - Docker Compose configuration
- `requirements.txt` - Python dependencies

---

## Setup Instructions

### 1. Local Setup

#### Prerequisites
- Python 3.10 or newer
- [pip](https://pip.pypa.io/en/stable/)
- (Recommended) [virtualenv](https://virtualenv.pypa.io/en/latest/)

#### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/PresentLM/PresentLM.git
   cd PresentLM
   ```
2. **Create and activate a virtual environment**
   - On Linux/Mac:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```
   - On Windows:
     ```bash
     python -m venv .venv
     .venv\Scripts\activate
     ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
4. **Configure environment variables**
   - Copy the example environment file and edit it:
     ```bash
     cp .env.example .env
     # Edit .env and set OPENAI_API_KEY=your-openai-key
     ```
5. **Run the application**
   ```bash
   streamlit run src/ui/app.py
   ```

---

### 2. Docker Setup

#### Prerequisites
- [Docker](https://www.docker.com/get-started)
- [Docker Compose](https://docs.docker.com/compose/)

#### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/PresentLM/PresentLM.git
   cd PresentLM
   ```
2. **Create the environment file**
   ```bash
   echo "OPENAI_API_KEY=your-openai-key" > .env
   # Optionally edit .env for further configuration
   ```
3. **Start the application using Docker Compose**
   ```bash
   docker-compose up
   ```
   This will build and start the application. Access it via your browser at the address shown in the terminal (typically http://localhost:8501).

#### Using Provided Scripts
- On Windows, you can use `docker-start.bat` to start the application.
- On Linux/Mac, use `docker-start.sh`.

---

## Configuration

All configuration is managed via the `.env` file in the project root.

### Required
```
OPENAI_API_KEY=your-openai-key
```

### Optional
```
# LLM Settings
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini

# TTS Settings (OpenAI or local Qwen)
TTS_PROVIDER=openai          # or "qwen" for local
TTS_VOICE=alloy              # OpenAI: nova, alloy, echo, fable
# TTS_VOICE=en-Female1       # Qwen: en-Female1, zh-Female1

# Test Mode (skip audio generation to save API costs)
TEST_MODE=false
```

---

## Usage

1. Upload a PDF or PPTX file via the web interface.
2. Optionally, add context (e.g., "Explain to a 10-year-old").
3. Click "Generate Presentation" and wait for processing.
4. Use the player controls to present, navigate, and interact with the Q&A panel.
5. Presentations are auto-saved in the `data/` directory and can be loaded later.

---

## Tech Stack

- **UI**: Streamlit
- **LLM**: OpenAI GPT-4o / GPT-4o-mini
- **TTS**: OpenAI TTS or Qwen3-TTS (local)
- **STT**: OpenAI Whisper
- **Parsing**: PyMuPDF (PDF), python-pptx (PPTX)
