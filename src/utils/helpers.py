"""
Utility helper functions for PresentLM.
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime


def generate_file_hash(file_path: Path) -> str:
    """Generate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def save_json(data: Dict[str, Any], file_path: Path) -> None:
    """Save data to JSON file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(file_path: Path) -> Dict[str, Any]:
    """Load data from JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def format_timestamp(seconds: float) -> str:
    """Format seconds to MM:SS format."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def save_presentation_data(timestamp: str, slides: List, narrations: List, audio_segments: List, metadata: Dict, base_dir: Path) -> None:
    """Save complete presentation data for later loading."""
    # Save slides
    slides_data = [slide.to_dict() for slide in slides]
    save_json({"slides": slides_data}, base_dir / f"{timestamp}_slides.json")
    
    # Save narrations
    narrations_data = [narration.to_dict() for narration in narrations]
    save_json({"narrations": narrations_data}, base_dir / f"{timestamp}_narrations.json")
    
    # Save audio segments info
    audio_data = [segment.to_dict() for segment in audio_segments] if audio_segments else []
    save_json({"audio_segments": audio_data}, base_dir / f"{timestamp}_audio.json")
    
    # Save metadata
    save_json(metadata, base_dir / f"{timestamp}_metadata.json")


def load_presentation_data(timestamp: str, base_dir: Path) -> Dict:
    """Load complete presentation data from saved files."""
    from ..core.slide_parser import Slide
    from ..core.narration_generator import SlideNarration
    from ..core.tts_engine import AudioSegment
    
    # Load slides
    slides_data = load_json(base_dir / f"{timestamp}_slides.json")
    slides = [Slide.from_dict(s) for s in slides_data['slides']]
    
    # Load narrations
    narrations_data = load_json(base_dir / f"{timestamp}_narrations.json")
    narrations = [SlideNarration.from_dict(n) for n in narrations_data['narrations']]
    
    # Load audio segments
    audio_file = base_dir / f"{timestamp}_audio.json"
    audio_segments = []
    if audio_file.exists():
        audio_data = load_json(audio_file)
        audio_segments = [AudioSegment.from_dict(a) for a in audio_data['audio_segments']]
    
    # Load metadata
    metadata = load_json(base_dir / f"{timestamp}_metadata.json")
    
    return {
        "slides": slides,
        "narrations": narrations,
        "audio_segments": audio_segments,
        "metadata": metadata
    }


def get_saved_presentations(base_dir: Path) -> List[Dict]:
    """Get list of all saved presentations."""
    presentations = []
    for metadata_file in sorted(base_dir.glob("*_metadata.json"), reverse=True):
        try:
            metadata = load_json(metadata_file)
            presentations.append(metadata)
        except Exception:
            continue
    return presentations


def estimate_audio_duration(text: str, words_per_minute: int = 150) -> float:
    """Estimate audio duration based on text length."""
    word_count = len(text.split())
    duration_minutes = word_count / words_per_minute
    return duration_minutes * 60  # Return in seconds


def chunk_text(text: str, max_chars: int = 5000) -> List[str]:
    """Split text into chunks at sentence boundaries."""
    sentences = text.replace('\n', ' ').split('. ')
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 2 <= max_chars:
            current_chunk += sentence + ". "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + ". "
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


def get_timestamp() -> str:
    """Get current timestamp string."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def sanitize_filename(filename: str) -> str:
    """Remove invalid characters from filename."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename
