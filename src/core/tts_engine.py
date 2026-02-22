"""
Text-to-Speech Engine - Converts narration text to natural speech audio.
Supports OpenAI and Qwen (local) TTS providers.
"""

import warnings
import os

# Suppress common warnings from TTS libraries
warnings.filterwarnings('ignore', category=UserWarning)
os.environ['PYTHONWARNINGS'] = 'ignore::UserWarning'

from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import openai
import numpy as np
import soundfile as sf

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
            provider: TTS provider (openai, qwen)
            voice: Voice name/ID (for OpenAI: alloy, echo, fable, onyx, nova, shimmer;
                   for Qwen: speaker names like 'en-Female1', 'en-Male1', etc.)
        """
        self.provider = provider or Config.TTS_PROVIDER
        self.voice = voice or Config.TTS_VOICE
        
        if self.provider == "openai":
            self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        elif self.provider == "qwen":
            # Load Qwen3-TTS model locally
            from qwen_tts.inference.qwen3_tts_model import Qwen3TTSModel
            import torch

            print(f"Loading Qwen3-TTS model...")

            # Force CPU - RTX 5070 sm_120 not supported by PyTorch
            self.device = torch.device("cpu")

            print(f"Using device: {self.device}")

            # Load with explicit CPU device
            self.client = Qwen3TTSModel.from_pretrained(
                "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
                torch_dtype=torch.float32,
                low_cpu_mem_usage=False
            )

            # Move model to CPU explicitly
            self.client.model = self.client.model.to(self.device)

            if hasattr(self.client.model, 'config'):
                self.client.model.config.use_cache = True

            print(f"✅ Qwen3-TTS model loaded successfully on {self.device}")
        else:
            raise ValueError(f"Unsupported TTS provider: {self.provider}. Supported: openai, qwen")

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
        elif self.provider == "qwen":
            segment = self._generate_qwen(text, output_path, speed)
        else:
            raise ValueError(f"Unsupported TTS provider: {self.provider}. Supported: openai, qwen")

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

    def _generate_qwen(self, text: str, output_path: Path, speed: float) -> AudioSegment:
        """Generate audio using Qwen3-TTS (local model)."""
        import torch

        try:
            # Detect language from text
            language = self._detect_language(text)

            # Use inference mode for faster generation
            with torch.inference_mode():
                # Generate audio using Qwen3-TTS with optimizations
                audio_arrays, sample_rate = self.client.generate_custom_voice(
                    text=text,
                    speaker=self.voice,
                    language=language,
                    non_streaming_mode=True,
                    do_sample=True,
                    top_k=20,
                    top_p=0.95,
                    temperature=0.7,
                    max_new_tokens=2048,  # Limit for faster generation
                )

            # Combine audio arrays if multiple
            if len(audio_arrays) > 0:
                audio = audio_arrays[0]
            else:
                raise ValueError("No audio generated")

            # Save audio file
            sf.write(str(output_path), audio, sample_rate)

            # Calculate actual duration
            duration = len(audio) / sample_rate

            return AudioSegment(
                slide_number=0,  # Will be set by caller
                audio_path=output_path,
                duration=duration,
                text=text
            )
        except Exception as e:
            raise ValueError(f"Qwen TTS generation failed: {e}")

    def _detect_language(self, text: str) -> str:
        """Simple language detection for Qwen TTS."""
        # Check for Chinese characters
        if any('\u4e00' <= char <= '\u9fff' for char in text):
            return 'chinese'
        # Default to English
        return 'english'


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
