"""
Speech-to-Text Engine - Converts user voice input to text for questions.
"""

from pathlib import Path
from typing import Optional, Union
import openai

from ..utils.config import Config
from ..utils.benchmark import get_benchmark_tracker


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
    
    def transcribe(self, audio_input: Union[Path, bytes]) -> str:
        """
        Transcribe audio to text.
        
        Args:
            audio_input: Path to audio file or audio bytes
            language: Language code
            
        Returns:
            Transcribed text
        """
        # Start benchmarking
        benchmark = get_benchmark_tracker()
        timer_id = f"transcribe_{id(self)}"
        benchmark.start_timer(timer_id)
        
        if self.provider == "openai":
            result = self._transcribe_openai(audio_input)
        else:
            raise ValueError(f"Unsupported STT provider: {self.provider}")
        
        # End benchmarking
        duration = benchmark.end_timer(
            timer_id,
            component="STTEngine",
            operation="transcribe",
            metadata={
                "provider": self.provider,
                "model": self.model,
                "input_type": "bytes" if isinstance(audio_input, bytes) else "file",
                "transcription_length": len(result)
            }
        )
        
        print(f"[BENCHMARK] STTEngine.transcribe: {duration:.2f}s ('{result[:50]}...')")
        
        return result
    
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
