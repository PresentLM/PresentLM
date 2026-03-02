"""
Benchmarking utility for tracking component latencies.
Records timing data for each component in the pipeline and provides export functionality.
"""

import time
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
from threading import RLock


@dataclass
class BenchmarkEvent:
    """Records a single benchmark event."""
    component: str  # e.g., "SlideParser", "NarrationGenerator", "TTSEngine", "STTEngine", "QuestionHandler"
    operation: str  # e.g., "parse", "generate_narration", "generate_audio", "transcribe", "answer_question"
    duration_seconds: float
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)  # Additional context (num_slides, model_used, etc.)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "component": self.component,
            "operation": self.operation,
            "duration_seconds": self.duration_seconds,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


class BenchmarkTracker:
    """Tracks benchmarks across the presentation pipeline."""
    
    def __init__(self, session_id: Optional[str] = None):
        """
        Initialize benchmark tracker.
        
        Args:
            session_id: Optional session identifier for grouping benchmarks
        """
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.events: List[BenchmarkEvent] = []
        self._start_times: Dict[str, float] = {}

        self._lock = RLock()
        self._output_path: Optional[Path] = None
        self._auto_save: bool = False

    def configure_persistence(self, filepath: Path, auto_save: bool = True) -> None:
        """Configure where benchmark data should be persisted.

        When auto_save is enabled, every recorded event will flush an updated JSON file.
        """
        with self._lock:
            self._output_path = filepath
            self._auto_save = auto_save

    def _persist_if_configured(self) -> None:
        with self._lock:
            if not (self._auto_save and self._output_path):
                return
            self.save_json(self._output_path, verbose=False)
    
    def start_timer(self, timer_id: str) -> None:
        """Start a timer with the given ID."""
        with self._lock:
            self._start_times[timer_id] = time.time()
    
    def end_timer(
        self, 
        timer_id: str, 
        component: str, 
        operation: str, 
        metadata: Optional[Dict] = None
    ) -> float:
        """
        End a timer and record the benchmark.
        
        Args:
            timer_id: The timer ID started with start_timer
            component: Component name
            operation: Operation name
            metadata: Optional metadata to store
            
        Returns:
            Duration in seconds
        """
        with self._lock:
            if timer_id not in self._start_times:
                raise ValueError(f"Timer '{timer_id}' was never started")

            duration = time.time() - self._start_times[timer_id]
            del self._start_times[timer_id]

            event = BenchmarkEvent(
                component=component,
                operation=operation,
                duration_seconds=duration,
                metadata=metadata or {}
            )
            self.events.append(event)

        self._persist_if_configured()
        return duration
    
    def record_event(
        self,
        component: str,
        operation: str,
        duration_seconds: float,
        metadata: Optional[Dict] = None
    ) -> None:
        """Record a benchmark event directly."""
        with self._lock:
            event = BenchmarkEvent(
                component=component,
                operation=operation,
                duration_seconds=duration_seconds,
                metadata=metadata or {}
            )
            self.events.append(event)

        self._persist_if_configured()
    
    def get_summary(self) -> Dict:
        """Get summary statistics by component and operation."""
        with self._lock:
            summary = {}

            for event in self.events:
                key = f"{event.component}::{event.operation}"
                if key not in summary:
                    summary[key] = {
                        "count": 0,
                        "total_time": 0.0,
                        "min_time": float('inf'),
                        "max_time": 0.0,
                        "avg_time": 0.0
                    }

                summary[key]["count"] += 1
                summary[key]["total_time"] += event.duration_seconds
                summary[key]["min_time"] = min(summary[key]["min_time"], event.duration_seconds)
                summary[key]["max_time"] = max(summary[key]["max_time"], event.duration_seconds)
                summary[key]["avg_time"] = summary[key]["total_time"] / summary[key]["count"]

            return summary
    
    def to_dict(self) -> Dict:
        """Convert all events to dictionary format."""
        with self._lock:
            return {
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "events": [event.to_dict() for event in self.events],
                "summary": self.get_summary()
            }
    
    def save_json(self, filepath: Path, verbose: bool = True) -> None:
        """Save benchmark data to JSON file."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = filepath.with_suffix(filepath.suffix + ".tmp")

        with self._lock:
            payload = self.to_dict()

        with open(tmp_path, 'w') as f:
            json.dump(payload, f, indent=2)
            f.flush()

        tmp_path.replace(filepath)
        if verbose:
            print(f"Benchmark data saved to {filepath}")
    
    def load_json(self, filepath: Path) -> None:
        """Load benchmark data from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)

        with self._lock:
            self.session_id = data.get("session_id", self.session_id)
            self.events = []

            for event_data in data.get("events", []):
                event = BenchmarkEvent(
                    component=event_data["component"],
                    operation=event_data["operation"],
                    duration_seconds=event_data["duration_seconds"],
                    timestamp=datetime.fromisoformat(event_data["timestamp"]),
                    metadata=event_data.get("metadata", {})
                )
                self.events.append(event)
    
    def print_summary(self) -> None:
        """Print a formatted summary of benchmarks."""
        summary = self.get_summary()
        
        print("\n" + "=" * 80)
        print("BENCHMARK SUMMARY")
        print("=" * 80)
        
        for key, stats in sorted(summary.items()):
            component, operation = key.split("::")
            print(f"\n{component} :: {operation}")
            print(f"  Count:     {stats['count']}")
            print(f"  Total:     {stats['total_time']:.2f}s")
            print(f"  Average:   {stats['avg_time']:.2f}s")
            print(f"  Min:       {stats['min_time']:.2f}s")
            print(f"  Max:       {stats['max_time']:.2f}s")
        
        print("\n" + "=" * 80)
        with self._lock:
            total_time = sum(event.duration_seconds for event in self.events)
        print(f"TOTAL PIPELINE TIME: {total_time:.2f}s")
        print("=" * 80 + "\n")


# Global benchmark tracker instance
_benchmark_tracker: Optional[BenchmarkTracker] = None


def get_benchmark_tracker(session_id: Optional[str] = None) -> BenchmarkTracker:
    """Get or create the global benchmark tracker."""
    global _benchmark_tracker
    if _benchmark_tracker is None:
        _benchmark_tracker = BenchmarkTracker(session_id)
    return _benchmark_tracker


def reset_benchmark_tracker() -> None:
    """Reset the global benchmark tracker."""
    global _benchmark_tracker
    _benchmark_tracker = None
