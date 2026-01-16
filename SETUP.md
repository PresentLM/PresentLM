# PresentLM Setup Guide

## Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- At least one API key (OpenAI, Anthropic, or ElevenLabs)

## Installation Steps

### 1. Clone or Navigate to the Repository

```bash
cd c:\Users\moham\Desktop\Master\GenAI\PresentLM
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
# Copy the example environment file
copy .env.example .env

# Edit .env with your favorite text editor
notepad .env
```

Add your API keys to `.env`:
```env
OPENAI_API_KEY=sk-your-key-here
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo
TTS_PROVIDER=openai
TTS_VOICE=alloy
STT_PROVIDER=openai
```

### 5. Test Configuration

```bash
python -c "from src.utils import Config; Config.validate(); print('✅ Configuration valid!')"
```

## Running the Application

### Option 1: Streamlit UI (Recommended)

```bash
streamlit run src/ui/app.py
```

Then open your browser to `http://localhost:8501`

### Option 2: Example Script

```bash
# Place a sample PDF in data/slides/example_presentation.pdf first
python example.py
```

## Quick Start Guide

1. **Upload a Presentation**
   - Start the Streamlit app
   - Upload a PDF or PPTX file
   - Optionally add context/notes
   - Click "Generate Presentation"

2. **Navigate the Presentation**
   - Use Previous/Next buttons
   - Click on slides in the navigator
   - Play audio narration for each slide

3. **Ask Questions**
   - Type questions in the Q&A panel
   - Get AI-generated answers based on slide content

## Recommended Configurations

### For Testing (Free/Low Cost)
```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-3.5-turbo
TTS_PROVIDER=edge
TTS_VOICE=en-US-AriaNeural
STT_PROVIDER=openai
```

### For Production (High Quality)
```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo
TTS_PROVIDER=openai
TTS_VOICE=alloy
STT_PROVIDER=openai
```

### For Image-Heavy Presentations
```env
LLM_PROVIDER=google
LLM_MODEL=gemini-1.5-pro
TTS_PROVIDER=openai
TTS_VOICE=alloy
STT_PROVIDER=openai
```

## Troubleshooting

### "Module not found" errors
```bash
# Make sure you're in the virtual environment
pip install -r requirements.txt
```

### API Key errors
```bash
# Verify your .env file has the correct keys
# No spaces around the = sign
OPENAI_API_KEY=sk-...
```

### Audio playback issues
```bash
# Install pygame dependencies
pip install pygame --upgrade
```

### PDF parsing errors
```bash
# Install PyMuPDF dependencies
pip install PyMuPDF --upgrade
```

## Next Steps

1. Review `TECHNOLOGY_RECOMMENDATIONS.md` for detailed provider comparisons
2. Check the documentation at `PresentLM-doc/` for project details
3. Explore the code in `src/core/` to understand the architecture
4. Try different TTS voices and LLM models
5. Experiment with narration styles (educational, professional, casual)

## Support

For issues or questions:
1. Check the documentation
2. Review example.py for usage patterns
3. Consult TECHNOLOGY_RECOMMENDATIONS.md for provider-specific help

## Development

To contribute or modify:
1. Create a new branch
2. Make changes
3. Test with `pytest tests/`
4. Submit pull request

Happy presenting! 🎤
