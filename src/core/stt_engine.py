"""
Speech-to-Text Engine - Converts user voice input to text for questions.
"""

from pathlib import Path
from typing import Optional, Union
import openai
import io

from ..utils.config import Config


class STTEngine:
    """Speech-to-Text conversion engine."""
    
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize STT engine.
        
        Args:
            provider: STT provider (openai, google, azure)
            model: Model name
        """
        self.provider = provider or Config.STT_PROVIDER
        self.model = model or Config.STT_MODEL
        
        if self.provider == "openai":
            self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
    
    def transcribe(
        self,
        audio_input: Union[Path, bytes],
        language: str = "en-US"
    ) -> str:
        """
        Transcribe audio to text.
        
        Args:
            audio_input: Path to audio file or audio bytes
            language: Language code
            
        Returns:
            Transcribed text
        """
        if self.provider == "openai":
            return self._transcribe_openai(audio_input)
        else:
            raise ValueError(f"Unsupported STT provider: {self.provider}")
    
    def _transcribe_openai(self, audio_input: Union[Path, bytes]) -> str:
        """Transcribe using OpenAI Whisper."""
        if isinstance(audio_input, bytes):
            # Save bytes to temporary file
            temp_path = Config.DATA_DIR / "temp_audio.wav"
            temp_path.write_bytes(audio_input)
            audio_input = temp_path
        
        with open(audio_input, "rb") as audio_file:
            transcript = self.client.audio.transcriptions.create(
                model=self.model,  # whisper-1
                file=audio_file,
                language=Config.STT_LANGUAGE
            )
        
        return transcript.text
    
    
    def transcribe_stream(self, audio_stream) -> str:
        """
        Transcribe streaming audio (for real-time voice input).
        
        Args:
            audio_stream: Audio stream generator
            
        Returns:
            Transcribed text
        """
        # TODO: Implement streaming transcription
        # This is useful for real-time voice questions
        raise NotImplementedError("Streaming transcription not yet implemented")
