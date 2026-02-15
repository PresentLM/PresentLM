# Core module initialization
from .slide_parser import SlideParser, Slide
from .narration_generator import NarrationGenerator, SlideNarration
from .tts_engine import TTSEngine, AudioSegment
from .stt_engine import STTEngine
from .question_handler import QuestionHandler, QuestionAnswer

__all__ = [
    "SlideParser",
    "Slide",
    "NarrationGenerator",
    "SlideNarration",
    "TTSEngine",
    "AudioSegment",
    "STTEngine",
    "QuestionHandler",
    "QuestionAnswer",
]
