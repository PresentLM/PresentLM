"""
Configuration management for PresentLM.
Loads environment variables and provides centralized config access.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration."""
    
    # Project paths
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    DATA_DIR = PROJECT_ROOT / "data"
    SLIDES_DIR = DATA_DIR / "slides"
    NARRATIONS_DIR = DATA_DIR / "narrations"
    AUDIO_DIR = DATA_DIR / "audio"
    
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

    # LLM Configuration
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # openai, anthropic, google
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4-turbo")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2000"))
    
    # TTS Configuration
    TTS_PROVIDER = os.getenv("TTS_PROVIDER", "openai")  # openai, elevenlabs, google, edge
    TTS_VOICE = os.getenv("TTS_VOICE", "alloy")
    TTS_SPEED = float(os.getenv("TTS_SPEED", "1.0"))
    
    # STT Configuration
    STT_PROVIDER = os.getenv("STT_PROVIDER", "openai")  # openai, google, azure
    STT_MODEL = os.getenv("STT_MODEL", "whisper-1")
    STT_LANGUAGE = os.getenv("STT_LANGUAGE", "en")
    
    # Application Settings
    MAX_SLIDES = int(os.getenv("MAX_SLIDES", "100"))
    AUDIO_FORMAT = os.getenv("AUDIO_FORMAT", "mp3")
    PRESENTATION_MODE = os.getenv("PRESENTATION_MODE", "auto")  # auto, manual
    TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"  # Skip TTS in test mode
    
    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist."""
        for directory in [cls.DATA_DIR, cls.SLIDES_DIR, cls.NARRATIONS_DIR, cls.AUDIO_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def validate(cls):
        """Validate that required configuration is present."""
        errors = []
        
        if cls.LLM_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is required when using OpenAI LLM")
        
        if cls.LLM_PROVIDER == "anthropic" and not cls.ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY is required when using Anthropic LLM")

        if cls.TTS_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is required when using OpenAI TTS")

        # Qwen TTS runs locally - no API key validation needed

        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))
        
        return True


# Initialize directories on import
Config.ensure_directories()
