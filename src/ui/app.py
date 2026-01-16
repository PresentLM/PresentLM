"""
PresentLM - Streamlit UI
Interactive presentation viewer with AI narration and Q&A.
"""

import streamlit as st
from pathlib import Path
import sys
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core import (
    SlideParser, NarrationGenerator, TTSEngine, STTEngine,
    TemporalSynchronizer, InteractionHandler, QuestionHandler,
    InteractionType, InteractionEvent
)
from src.utils import Config, save_json, load_json, get_timestamp, sanitize_filename


# Page config
st.set_page_config(
    page_title="PresentLM",
    layout="wide"
)

# Session state initialization
if "presentation_loaded" not in st.session_state:
    st.session_state.presentation_loaded = False
if "slides" not in st.session_state:
    st.session_state.slides = []
if "narrations" not in st.session_state:
    st.session_state.narrations = []
if "current_slide_idx" not in st.session_state:
    st.session_state.current_slide_idx = 0


def main():
    """Main application."""
    
    st.title("PresentLM")
    st.markdown("*Turn static slides into interactive, spoken experiences*")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        # LLM Model
        llm_model = st.selectbox(
            "LLM Model",
            ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
            index=0
        )
        
        # Test mode
        test_mode = st.checkbox("Test Mode (text only, no audio)", value=True)
        
        # Voice selection (only if not in test mode)
        if not test_mode:
            tts_voice = st.selectbox(
                "Voice",
                ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
            )
        else:
            tts_voice = "alloy"
        
        # Narration style
        narration_style = st.selectbox(
            "Narration Style",
            ["educational", "professional", "casual"]
        )
        
        st.divider()
        
        # About
        st.markdown("""
        ### About PresentLM
        
        PresentLM is an AI-driven system that:
        - Parses slide decks (PDF/PPT)
        - Generates natural narration
        - Converts to speech
        - Synchronizes slides with audio
        - Answers questions interactively
        """)
    
    # Main content area
    if not st.session_state.presentation_loaded:
        show_upload_page(llm_model, test_mode, tts_voice, narration_style)
    else:
        show_presentation_page()


def show_upload_page(llm_model, test_mode, tts_voice, narration_style):
    """Show file upload and processing page."""
    
    st.header("Upload Presentation")
    
    uploaded_file = st.file_uploader(
        "Choose a slide deck (PDF or PPTX)",
        type=["pdf", "pptx"]
    )
    
    additional_context = st.text_area(
        "Additional Context (optional)",
        placeholder="Lecture notes, supporting materials, or context for narration generation...",
        height=150
    )
    
    if uploaded_file:
        if st.button("Generate Presentation", type="primary"):
            process_presentation(
                uploaded_file,
                additional_context,
                llm_model,
                test_mode,
                tts_voice,
                narration_style
            )


def process_presentation(
    uploaded_file,
    context,
    llm_model,
    test_mode,
    tts_voice,
    narration_style
):
    """Process uploaded presentation."""
    
    # Validate API keys before processing
    try:
        Config.validate()
    except ValueError as e:
        st.error(f"Configuration Error: {e}")
        st.info("Please set up your API key in the .env file to generate presentations.")
        st.code("""
# Create .env file with:
OPENAI_API_KEY=sk-your-key-here
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
TTS_PROVIDER=openai
TTS_VOICE=alloy
TEST_MODE=true
        """, language="bash")
        return
    
    with st.spinner("Processing presentation..."):
        # Save uploaded file
        timestamp = get_timestamp()
        filename = sanitize_filename(uploaded_file.name)
        file_path = Config.SLIDES_DIR / f"{timestamp}_{filename}"
        
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Parse slides
        st.info("Parsing slides...")
        parser = SlideParser(use_vision=False)
        slides = parser.parse(file_path)
        
        st.success(f"Parsed {len(slides)} slides")
        
        # Generate narrations
        st.info("Generating narrations...")
        narration_gen = NarrationGenerator(provider="openai", model=llm_model)
        narrations = narration_gen.generate_narration(
            slides,
            context=context if context else None,
            style=narration_style
        )
        
        st.success(f"Generated {len(narrations)} narrations")
        
        # Generate audio (skip in test mode to save tokens)
        audio_segments = []
        if test_mode:
            st.info("Test mode enabled - Skipping TTS generation to save tokens")
        else:
            st.info("Converting to speech...")
            tts = TTSEngine(provider="openai", voice=tts_voice)
            
            progress_bar = st.progress(0)
            
            for idx, narration in enumerate(narrations):
                audio_path = Config.AUDIO_DIR / f"{timestamp}_slide_{narration.slide_number}.mp3"
                segment = tts.generate_audio(narration.narration_text, audio_path)
                segment.slide_number = narration.slide_number
                audio_segments.append(segment)
                
                progress_bar.progress((idx + 1) / len(narrations))
            
            st.success("Audio generation complete!")
        
        # Save to session state
        st.session_state.slides = slides
        st.session_state.narrations = narrations
        st.session_state.audio_segments = audio_segments
        st.session_state.presentation_loaded = True
        st.session_state.current_slide_idx = 0
        
        # Save metadata
        metadata = {
            "timestamp": timestamp,
            "filename": filename,
            "num_slides": len(slides),
            "llm_provider": llm_provider,
            "tts_provider": tts_provider,
            "narration_style": narration_style
        }
        save_json(metadata, Config.DATA_DIR / f"{timestamp}_metadata.json")
        
        st.rerun()


def show_presentation_page():
    """Show presentation viewer."""
    
    slides = st.session_state.slides
    narrations = st.session_state.narrations
    current_idx = st.session_state.current_slide_idx
    
    # Top controls
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 2])
    
    with col1:
        if st.button("Previous"):
            if current_idx > 0:
                st.session_state.current_slide_idx -= 1
                st.rerun()
    
    with col2:
        if st.button("Next"):
            if current_idx < len(slides) - 1:
                st.session_state.current_slide_idx += 1
                st.rerun()
    
    with col3:
        st.write(f"Slide {current_idx + 1}/{len(slides)}")
    
    with col5:
        if st.button("🔄 New Presentation"):
            st.session_state.presentation_loaded = False
            st.rerun()
    
    # Current slide display
    current_slide = slides[current_idx]
    current_narration = narrations[current_idx]
    
    st.divider()
    
    # Two columns: slide content and controls
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.subheader(f"Slide {current_slide.slide_number}: {current_slide.title}")
        
        # Slide content
        with st.container(border=True):
            st.markdown(current_slide.content)
            
            if current_slide.notes:
                with st.expander("📝 Speaker Notes"):
                    st.markdown(current_slide.notes)
        
        # Narration
        st.subheader("Narration")
        st.write(current_narration.narration_text)
        
        # Audio player (only if not in test mode)
        if hasattr(st.session_state, 'audio_segments') and st.session_state.audio_segments:
            audio_segment = st.session_state.audio_segments[current_idx]
            if audio_segment.audio_path.exists():
                st.audio(str(audio_segment.audio_path))
        elif Config.TEST_MODE:
            st.info("Test mode: Audio generation skipped. Enable TTS by disabling Test Mode checkbox")
    
    with col_right:
        st.subheader("Ask Questions")
        
        question = st.text_input("Type your question:")
        
        if st.button("Ask", type="primary") and question:
            # TODO: Integrate with QuestionHandler
            with st.spinner("Thinking..."):
                st.info("Question answering will be integrated with the QuestionHandler component.")
                st.write(f"**Q:** {question}")
                st.write("**A:** This feature is coming soon!")
        
        st.divider()
        
        # Slide navigator
        st.subheader("📑 Slide Navigator")
        for idx, slide in enumerate(slides):
            if st.button(
                f"{idx + 1}. {slide.title[:30]}...",
                key=f"nav_{idx}",
                use_container_width=True
            ):
                st.session_state.current_slide_idx = idx
                st.rerun()


if __name__ == "__main__":
    main()
