"""
Text-to-Speech Engine - Converts narration text to natural speech audio.
Supports multiple TTS providers.
"""

from pathlib import Path
from typing import Optional, Literal
from dataclasses import dataclass
import openai
import asyncio

from ..utils.config import Config
from ..utils.benchmark import get_benchmark_tracker


@dataclass
class AudioSegment:
    """Represents an audio segment for a slide."""
    slide_number: int
    audio_path: Path
    duration: float  # in seconds
    text: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "slide_number": self.slide_number,
            "audio_path": str(self.audio_path),
            "duration": self.duration,
            "text": self.text
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AudioSegment':
        """Create from dictionary."""
        return cls(
            slide_number=data['slide_number'],
            audio_path=Path(data['audio_path']),
            duration=data['duration'],
            text=data['text']
        )


class TTSEngine:
    """Text-to-Speech conversion engine."""
    
    def __init__(self, provider: Optional[str] = None, voice: Optional[str] = None):
        """
        Initialize TTS engine.
        
        Args:
            provider: TTS provider (openai, elevenlabs, google, edge)
            voice: Voice name/ID
        """
        self.provider = provider or Config.TTS_PROVIDER
        self.voice = voice or Config.TTS_VOICE
        
        if self.provider == "openai":
            self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
    
    def generate_audio(
        self,
        text: str,
        output_path: Path,
        speed: float = 1.0
    ) -> AudioSegment:
        """
        Generate audio from text.
        
        Args:
            text: Text to convert to speech
            output_path: Where to save the audio file
            speed: Speech speed multiplier
            
        Returns:
            AudioSegment with metadata
        """
        # Start benchmarking
        benchmark = get_benchmark_tracker()
        timer_id = f"generate_audio_{id(self)}"
        benchmark.start_timer(timer_id)
        
        if self.provider == "openai":
            segment = self._generate_openai(text, output_path, speed)
        else:
            raise ValueError(f"Unsupported TTS provider: {self.provider}")
        
        # End benchmarking
        duration = benchmark.end_timer(
            timer_id,
            component="TTSEngine",
            operation="generate_audio",
            metadata={
                "provider": self.provider,
                "voice": self.voice,
                "text_length": len(text),
                "word_count": len(text.split()),
                "audio_duration": segment.duration
            }
        )
        
        print(f"[BENCHMARK] TTSEngine.generate_audio: {duration:.2f}s ({len(text.split())} words, {segment.duration:.1f}s audio)")
        
        return segment
    
    def _generate_openai(self, text: str, output_path: Path, speed: float) -> AudioSegment:
        """Generate audio using OpenAI TTS."""
        response = self.client.audio.speech.create(
            model="tts-1-hd",  # or "tts-1" for faster/cheaper
            voice=self.voice,  # alloy, echo, fable, onyx, nova, shimmer
            input=text,
            speed=speed
        )
        
        # Save audio file
        response.stream_to_file(output_path)
        
        # Estimate duration (OpenAI doesn't provide it directly)
        word_count = len(text.split())
        duration = (word_count / 150) * 60 / speed
        
        return AudioSegment(
            slide_number=0,  # Will be set by caller
            audio_path=output_path,
            duration=duration,
            text=text
        )
    
    
    def batch_generate(
        self,
        texts: list[tuple[str, Path]],
        speed: float = 1.0
    ) -> list[AudioSegment]:
        """
        Generate audio for multiple texts.
        
        Args:
            texts: List of (text, output_path) tuples
            speed: Speech speed multiplier
            
        Returns:
            List of AudioSegment objects
        """
        segments = []
        for idx, (text, output_path) in enumerate(texts, start=1):
            segment = self.generate_audio(text, output_path, speed)
            segment.slide_number = idx
            segments.append(segment)
        
        return segments
