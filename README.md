# PresentLM

An AI-driven presentation system that turns static slide decks into interactive, spoken experiences.

## Project Structure

```
PresentLM/
├── src/
│   ├── core/
│   │   ├── slide_parser.py          # Extract content from slides
│   │   ├── narration_generator.py   # Generate narration using LLM
│   │   ├── tts_engine.py            # Text-to-Speech conversion
│   │   ├── stt_engine.py            # Speech-to-Text conversion
│   │   ├── temporal_sync.py         # Synchronize slides with audio
│   │   ├── interaction_handler.py   # Manage user interactions
│   │   └── question_handler.py      # Answer questions using LLM
│   ├── api/
│   │   └── server.py                # FastAPI backend
│   ├── ui/
│   │   └── app.py                   # Streamlit frontend
│   └── utils/
│       ├── config.py                # Configuration management
│       └── helpers.py               # Utility functions
├── data/
│   ├── slides/                      # Uploaded slide decks
│   ├── narrations/                  # Generated narrations
│   └── audio/                       # Generated audio files
├── tests/
│   └── test_*.py                    # Unit tests
├── requirements.txt
├── .env.example
└── README.md
```

## Technology Stack

### LLM (Language Model)
- **OpenAI GPT-4/GPT-4-turbo** - High quality, good for complex narration
- **Anthropic Claude 3.5 Sonnet** - Excellent for structured output
- **Google Gemini 1.5 Pro** - Good multimodal capabilities for image-heavy slides
- **Open Source: Llama 3.1** - Self-hosted option

### Speech-to-Text (STT)
- **OpenAI Whisper** - Excellent accuracy, open source, multiple languages
- **Google Cloud Speech-to-Text** - Real-time streaming, high accuracy
- **Azure Speech Services** - Good integration with enterprise systems
- **AssemblyAI** - Modern API, speaker diarization

### Text-to-Speech (TTS)
- **OpenAI TTS (tts-1, tts-1-hd)** - Natural voices, good quality
- **ElevenLabs** - Most natural-sounding, emotional range
- **Google Cloud TTS** - WaveNet voices, multilingual
- **Azure Neural TTS** - Natural voices, SSML support
- **Edge TTS** - Free Microsoft voices

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Edit .env with your API keys
```

## Quick Start

```bash
# Run the application
streamlit run src/ui/app.py
```

## Configuration

Set up your API keys in `.env`:

```env
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
ELEVENLABS_API_KEY=your_key_here
```
