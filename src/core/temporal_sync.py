"""
Temporal Synchronization - Manages slide progression in sync with audio narration.
"""

from typing import List, Optional, Callable
from dataclasses import dataclass
import time
from pathlib import Path
import pygame
from threading import Thread, Event

from .tts_engine import AudioSegment


@dataclass
class PresentationState:
    """Current state of the presentation."""
    current_slide: int
    is_playing: bool
    is_paused: bool
    current_time: float
    total_duration: float
    in_question_mode: bool = False


class TemporalSynchronizer:
    """Synchronize slide progression with audio narration."""
    
    def __init__(self, audio_segments: List[AudioSegment], auto_advance: bool = True):
        """
        Initialize temporal synchronizer.
        
        Args:
            audio_segments: List of audio segments for each slide
            auto_advance: Whether to auto-advance slides with audio
        """
        self.audio_segments = audio_segments
        self.auto_advance = auto_advance
        
        self.state = PresentationState(
            current_slide=1,
            is_playing=False,
            is_paused=False,
            current_time=0.0,
            total_duration=sum(seg.duration for seg in audio_segments)
        )
        
        # Initialize pygame mixer for audio playback
        pygame.mixer.init()
        
        # Callbacks
        self.on_slide_change: Optional[Callable[[int], None]] = None
        self.on_presentation_end: Optional[Callable[[], None]] = None
        
        # Control events
        self._stop_event = Event()
        self._pause_event = Event()
        self._playback_thread: Optional[Thread] = None
    
    def start_presentation(self):
        """Start the presentation from the beginning."""
        self.state.current_slide = 1
        self.state.is_playing = True
        self.state.is_paused = False
        self._stop_event.clear()
        
        # Start playback in separate thread
        self._playback_thread = Thread(target=self._playback_loop)
        self._playback_thread.start()
    
    def pause(self):
        """Pause the presentation."""
        if self.state.is_playing:
            self.state.is_paused = True
            pygame.mixer.music.pause()
            self._pause_event.set()
    
    def resume(self):
        """Resume the presentation."""
        if self.state.is_paused:
            self.state.is_paused = False
            pygame.mixer.music.unpause()
            self._pause_event.clear()
    
    def stop(self):
        """Stop the presentation."""
        self.state.is_playing = False
        self._stop_event.set()
        pygame.mixer.music.stop()
        
        if self._playback_thread:
            self._playback_thread.join(timeout=2.0)
    
    def next_slide(self):
        """Manually advance to next slide."""
        if self.state.current_slide < len(self.audio_segments):
            self.state.current_slide += 1
            if self.on_slide_change:
                self.on_slide_change(self.state.current_slide)
    
    def previous_slide(self):
        """Go back to previous slide."""
        if self.state.current_slide > 1:
            self.state.current_slide -= 1
            if self.on_slide_change:
                self.on_slide_change(self.state.current_slide)
    
    def go_to_slide(self, slide_number: int):
        """Jump to a specific slide."""
        if 1 <= slide_number <= len(self.audio_segments):
            self.state.current_slide = slide_number
            if self.on_slide_change:
                self.on_slide_change(self.state.current_slide)
    
    def interrupt_for_question(self):
        """Pause presentation for user question."""
        self.state.in_question_mode = True
        self.pause()
    
    def resume_after_question(self):
        """Resume presentation after answering question."""
        self.state.in_question_mode = False
        self.resume()
    
    def _playback_loop(self):
        """Main playback loop running in separate thread."""
        for slide_idx, segment in enumerate(self.audio_segments, start=1):
            if self._stop_event.is_set():
                break
            
            # Update current slide
            self.state.current_slide = slide_idx
            if self.on_slide_change:
                self.on_slide_change(slide_idx)
            
            # Play audio for this slide
            if not self.auto_advance:
                # Manual mode: just play audio, don't auto-advance
                self._play_audio(segment.audio_path)
                break  # Wait for manual advancement
            else:
                # Auto mode: play and advance
                self._play_audio(segment.audio_path)
                
                # Wait for audio to finish
                while pygame.mixer.music.get_busy():
                    if self._stop_event.is_set():
                        pygame.mixer.music.stop()
                        return
                    
                    # Check for pause
                    if self._pause_event.is_set():
                        self._pause_event.wait()
                    
                    time.sleep(0.1)
        
        # Presentation finished
        self.state.is_playing = False
        if self.on_presentation_end:
            self.on_presentation_end()
    
    def _play_audio(self, audio_path: Path):
        """Play audio file."""
        try:
            pygame.mixer.music.load(str(audio_path))
            pygame.mixer.music.play()
        except pygame.error as e:
            print(f"Error playing audio: {e}")
    
    def get_progress(self) -> float:
        """Get presentation progress as percentage."""
        if self.state.total_duration == 0:
            return 0.0
        
        elapsed = sum(
            seg.duration for seg in self.audio_segments[:self.state.current_slide - 1]
        )
        
        return (elapsed / self.state.total_duration) * 100
    
    def get_state(self) -> PresentationState:
        """Get current presentation state."""
        return self.state
