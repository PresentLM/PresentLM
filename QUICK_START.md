# PresentLM Quick Reference

## Installation (30 seconds)
```bash
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Edit .env with your OpenAI API key
streamlit run src/ui/app.py
```

## Minimum .env Configuration
```env
OPENAI_API_KEY=sk-proj-...your-key...
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo
TTS_PROVIDER=openai
TTS_VOICE=alloy
STT_PROVIDER=openai
```

## File Structure at a Glance
```
PresentLM/
├── src/core/              # 7 core modules (parser, narration, tts, stt, sync, Q&A, handler)
├── src/ui/app.py          # Streamlit interface
├── src/utils/             # Config & helpers
├── data/                  # Generated content (slides/narrations/audio)
├── requirements.txt       # Dependencies
└── .env                   # Your API keys (create from .env.example)
```

## Core Components
| Component | File | Purpose |
|-----------|------|---------|
| **Slide Parser** | `slide_parser.py` | PDF/PPT → structured slides |
| **Narration Gen** | `narration_generator.py` | Slides → AI narration text |
| **TTS Engine** | `tts_engine.py` | Text → audio (mp3) |
| **STT Engine** | `stt_engine.py` | Voice → text (for questions) |
| **Temporal Sync** | `temporal_sync.py` | Sync slides + audio playback |
| **Question Handler** | `question_handler.py` | Answer questions via LLM |
| **Interaction Handler** | `interaction_handler.py` | Route user actions |

## Provider Options

### LLM
- `openai`

### TTS
- `openai` + `alloy/nova/shimmer` (good quality)
- `elevenlabs` + `voice_id` (best quality, paid)
- `edge` + `en-US-AriaNeural` (free!)

### STT
- `openai` + `whisper-1` (recommended)
- `google` (streaming support)

## Common Commands
```bash
# Validate config
python -c "from src.utils import Config; Config.validate()"

# Run UI
streamlit run src/ui/app.py

# Run example
python example.py

# Install specific provider
pip install openai anthropic elevenlabs edge-tts
```

## Typical Workflow
1. **Upload**: PDF or PPTX via UI
2. **Configure**: Select LLM/TTS/style
3. **Generate**: Click "Generate Presentation"
   - Parses slides (5-10s)
   - Generates narration (30-60s)
   - Creates audio (30-90s)
4. **Present**: Navigate slides, hear narration
5. **Interact**: Ask questions anytime

## Cost Estimates (per presentation)
| Config | 30 slides | Notes |
|--------|-----------|-------|
| Budget | $0.60 | GPT-4 + Edge TTS (free) |
| Standard | $0.83 | GPT-4 + OpenAI TTS |
| Premium | $1.95 | GPT-4 + ElevenLabs |

## Troubleshooting
```bash
# Module errors
pip install -r requirements.txt --upgrade

# API key errors
# Check .env has: OPENAI_API_KEY=sk-...
# No spaces around =

# Audio issues
pip install pygame --upgrade

# PDF parsing
pip install PyMuPDF --upgrade
```

## Key Features
✅ Parse PDF/PPT slides  
✅ AI-generated narration  
✅ Natural text-to-speech  
✅ Synced slide playback  
✅ Interactive Q&A  
✅ Voice questions  
✅ Multiple providers  
✅ Human-in-the-loop design  

## Documentation
- **Setup**: `SETUP.md`
- **Architecture**: `ARCHITECTURE.md`
- **Tech Details**: `TECHNOLOGY_RECOMMENDATIONS.md`
- **Full Summary**: `PROJECT_SUMMARY.md`
- **Web Docs**: `PresentLM-doc/docs/`

## Quick Tips
💡 Start with Edge TTS (free) for testing  
💡 Use GPT-3.5-turbo for cheaper narration  
💡 Educational style works best for lectures  
💡 Add context/notes for better narration  
💡 Pause presentation before asking questions  

## Support
- Check `SETUP.md` for detailed setup
- See `example.py` for code examples
- Review `TECHNOLOGY_RECOMMENDATIONS.md` for provider details
- Browse `PresentLM-doc/` for full documentation

---
**Ready to transform your presentations? 🎤**
