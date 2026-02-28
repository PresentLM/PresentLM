# PresentLM

Transform presentations into interactive, narrated experiences with AI-powered Q&A.

## Features

✨ **AI Narration** - Automatic spoken explanations for slides  
🎙️ **Text-to-Speech** - OpenAI or local Qwen TTS  
💬 **Interactive Q&A** - Ask questions via text or voice  
▶️ **Auto-Play** - Synchronized audio and slide progression  
📄 **Multi-Format** - Supports PDF and PowerPoint files

---

## Quick Start (Docker)

```bash
# 1. Clone and enter directory
git clone https://github.com/PresentLM/PresentLM.git
cd PresentLM

# 2. Create .env file with your API key
echo "OPENAI_API_KEY=sk-your-key-here" > .env

# 3. Start with Docker
docker-compose up
```

**That's it!** Upload a presentation and start.

---

## Quick Start (Local)

```bash
# 1. Clone and enter directory
git clone https://github.com/PresentLM/PresentLM.git
cd PresentLM

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure API key
cp .env.example .env
# Edit .env and add: OPENAI_API_KEY=sk-your-key-here

# 5. Run application
streamlit run src/ui/app.py
```

---

## Configuration

### Required

```bash
OPENAI_API_KEY=sk-your-key-here
```

### Optional

```bash
# LLM Settings
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini

# TTS Settings (OpenAI or local Qwen)
TTS_PROVIDER=openai          # or "qwen" for local (free)
TTS_VOICE=alloy              # OpenAI: nova, alloy, echo, fable
# TTS_VOICE=en-Female1       # Qwen: en-Female1, zh-Female1

# Test Mode (skip audio generation to save API costs)
TEST_MODE=false
```

---

## Usage

### Upload & Generate

1. Upload PDF or PPTX file
2. Add optional context (e.g., "Explain to a 10-year-old")
3. Click **Generate Presentation**
4. Wait for processing (narration + optional audio)

### Present

- Use **Play** button for auto-play mode
- **Previous/Next** for manual navigation
- Click **Q&A** panel to ask questions (text or voice)
- Export narrations as text or PDF

### Save & Load

- Presentations auto-save after generation
- Load saved presentations from **Load Saved** tab
- All data stored in `data/` directory

---

## Tech Stack

- **UI**: Streamlit
- **LLM**: OpenAI GPT-4o / GPT-4o-mini
- **TTS**: OpenAI TTS or Qwen3-TTS (local)
- **STT**: OpenAI Whisper
- **Parse**: PyMuPDF (PDF), python-pptx (PPTX)

---
