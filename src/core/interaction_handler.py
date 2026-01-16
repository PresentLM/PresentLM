"""
Interaction Handler - Manages user interactions and routes requests to appropriate components.
"""

from typing import Optional, Callable
from enum import Enum
from dataclasses import dataclass

from .temporal_sync import TemporalSynchronizer, PresentationState
from .question_handler import QuestionHandler
from .stt_engine import STTEngine
from .tts_engine import TTSEngine


class InteractionType(Enum):
    """Types of user interactions."""
    PLAY = "play"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"
    NEXT_SLIDE = "next"
    PREVIOUS_SLIDE = "previous"
    GO_TO_SLIDE = "goto"
    ASK_QUESTION = "question"
    VOICE_QUESTION = "voice_question"


@dataclass
class InteractionEvent:
    """Represents a user interaction event."""
    interaction_type: InteractionType
    data: Optional[dict] = None


class InteractionHandler:
    """Central handler for all user interactions."""
    
    def __init__(
        self,
        synchronizer: TemporalSynchronizer,
        question_handler: QuestionHandler,
        stt_engine: STTEngine,
        tts_engine: TTSEngine
    ):
        """
        Initialize interaction handler.
        
        Args:
            synchronizer: Temporal synchronization manager
            question_handler: Question answering system
            stt_engine: Speech-to-text for voice questions
            tts_engine: Text-to-speech for audio responses
        """
        self.synchronizer = synchronizer
        self.question_handler = question_handler
        self.stt_engine = stt_engine
        self.tts_engine = tts_engine
        
        # Callbacks for UI updates
        self.on_state_change: Optional[Callable[[PresentationState], None]] = None
        self.on_question_answered: Optional[Callable[[str, str], None]] = None
    
    def handle_interaction(self, event: InteractionEvent):
        """
        Handle a user interaction event.
        
        Args:
            event: The interaction event to handle
        """
        if event.interaction_type == InteractionType.PLAY:
            self._handle_play()
        
        elif event.interaction_type == InteractionType.PAUSE:
            self._handle_pause()
        
        elif event.interaction_type == InteractionType.RESUME:
            self._handle_resume()
        
        elif event.interaction_type == InteractionType.STOP:
            self._handle_stop()
        
        elif event.interaction_type == InteractionType.NEXT_SLIDE:
            self._handle_next_slide()
        
        elif event.interaction_type == InteractionType.PREVIOUS_SLIDE:
            self._handle_previous_slide()
        
        elif event.interaction_type == InteractionType.GO_TO_SLIDE:
            self._handle_go_to_slide(event.data.get("slide_number"))
        
        elif event.interaction_type == InteractionType.ASK_QUESTION:
            self._handle_text_question(event.data.get("question"))
        
        elif event.interaction_type == InteractionType.VOICE_QUESTION:
            self._handle_voice_question(event.data.get("audio_data"))
        
        # Notify UI of state change
        if self.on_state_change:
            self.on_state_change(self.synchronizer.get_state())
    
    def _handle_play(self):
        """Handle play action."""
        self.synchronizer.start_presentation()
    
    def _handle_pause(self):
        """Handle pause action."""
        self.synchronizer.pause()
    
    def _handle_resume(self):
        """Handle resume action."""
        if self.synchronizer.state.in_question_mode:
            self.synchronizer.resume_after_question()
        else:
            self.synchronizer.resume()
    
    def _handle_stop(self):
        """Handle stop action."""
        self.synchronizer.stop()
        self.question_handler.clear_history()
    
    def _handle_next_slide(self):
        """Handle next slide action."""
        self.synchronizer.next_slide()
    
    def _handle_previous_slide(self):
        """Handle previous slide action."""
        self.synchronizer.previous_slide()
    
    def _handle_go_to_slide(self, slide_number: int):
        """Handle go to slide action."""
        if slide_number:
            self.synchronizer.go_to_slide(slide_number)
    
    def _handle_text_question(self, question: str):
        """Handle text-based question."""
        if not question:
            return
        
        # Pause presentation
        self.synchronizer.interrupt_for_question()
        
        # Get answer from question handler
        # Note: This requires current slide context, which should be passed
        # from the main application
        # For now, this is a placeholder
        answer = "Question received. Implementation needs slide context."
        
        # Notify UI
        if self.on_question_answered:
            self.on_question_answered(question, answer)
    
    def _handle_voice_question(self, audio_data: bytes):
        """Handle voice-based question."""
        if not audio_data:
            return
        
        # Convert speech to text
        question_text = self.stt_engine.transcribe(audio_data)
        
        # Handle as text question
        self._handle_text_question(question_text)
    
    def get_current_state(self) -> PresentationState:
        """Get current presentation state."""
        return self.synchronizer.get_state()
    
    def enable_voice_mode(self) -> bool:
        """
        Enable voice interaction mode.
        
        Returns:
            True if voice mode is available
        """
        # Check if STT is configured
        return self.stt_engine is not None
    
    def set_auto_advance(self, enabled: bool):
        """
        Enable or disable auto-advance mode.
        
        Args:
            enabled: Whether slides should auto-advance with audio
        """
        self.synchronizer.auto_advance = enabled
