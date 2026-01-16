# Core module initialization
from .slide_parser import SlideParser, Slide
from .narration_generator import NarrationGenerator, SlideNarration
from .tts_engine import TTSEngine, AudioSegment
from .stt_engine import STTEngine
from .temporal_sync import TemporalSynchronizer, PresentationState
from .interaction_handler import InteractionHandler, InteractionType, InteractionEvent
from .question_handler import QuestionHandler, QuestionAnswer

__all__ = [
    "SlideParser",
    "Slide",
    "NarrationGenerator",
    "SlideNarration",
    "TTSEngine",
    "AudioSegment",
    "STTEngine",
    "TemporalSynchronizer",
    "PresentationState",
    "InteractionHandler",
    "InteractionType",
    "InteractionEvent",
    "QuestionHandler",
    "QuestionAnswer",
]
