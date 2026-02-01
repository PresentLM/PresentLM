"""
PresentLM - Streamlit UI
Interactive presentation viewer with AI narration and Q&A.
"""

import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
import sys
from io import BytesIO
import time
import base64

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core import (
    SlideParser, NarrationGenerator, TTSEngine, STTEngine,
    TemporalSynchronizer, InteractionHandler, QuestionHandler,
    InteractionType, InteractionEvent
)
from src.utils import (
    Config, save_json, load_json, get_timestamp, sanitize_filename,
    save_presentation_data, load_presentation_data, get_saved_presentations
)


# Page config
st.set_page_config(
    page_title="PresentLM",
    page_icon="src/assets/PresentLM-logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'presentation_loaded' not in st.session_state:
    st.session_state.presentation_loaded = False
if 'current_slide_idx' not in st.session_state:
    st.session_state.current_slide_idx = 0
if 'is_paused' not in st.session_state:
    st.session_state.is_paused = False
if 'current_question' not in st.session_state:
    st.session_state.current_question = None
if 'current_answer' not in st.session_state:
    st.session_state.current_answer = None
if 'waiting_for_feedback' not in st.session_state:
    st.session_state.waiting_for_feedback = False
if 'audio_finished' not in st.session_state:
    st.session_state.audio_finished = False
if 'audio_position' not in st.session_state:
    st.session_state.audio_position = {}
if 'asking_question' not in st.session_state:
    st.session_state.asking_question = False
if 'poll_timestamp' not in st.session_state:
    st.session_state.poll_timestamp = time.time()
if 'advance_slide' not in st.session_state:
    st.session_state.advance_slide = False
if 'previous_slide_idx' not in st.session_state:
    st.session_state.previous_slide_idx = 0

# Enhanced header
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.image(
        "src/assets/PresentLM-logo.png",
        width="stretch"
    )

st.markdown("---")


def main():
    """Main application."""

    st.markdown(
        """
        <link
          rel="stylesheet"
          href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css"
          integrity="sha512-DTOQO9RWCH3ppGqcWaEA1BIZOC6xxalwEsw9c2QQeAIftl+Vegovlnee1c9QX4TctnWMn13TZye+giMm8e2LwA=="
          crossorigin="anonymous"
          referrerpolicy="no-referrer"
        />
        """,
        unsafe_allow_html=True
    )

    # Sidebar enhancements
    with st.sidebar:
        st.title("PresentLM Settings")
        st.markdown("---")
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

        st.markdown("---")

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

    # Footer
    st.markdown("---")

    st.markdown(
        """
        <div style="
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.4rem;
        ">
            <div style="font-size: 1.2rem;">
                <a href="https://presentlm.github.io/PresentLM/"
                   target="_blank"
                   style="margin-right: 0.75rem; color: inherit;"
                   title="Documentation">
                    <i class="fa-solid fa-book"></i>
                </a>
                <a href="https://github.com/PresentLM/PresentLM"
                   target="_blank"
                   style="color: inherit;"
                   title="GitHub">
                    <i class="fa-brands fa-github"></i>
                </a>
            </div>
            <div style="font-size: 0.75rem; color: #6b7280;">
                © 2026 PresentLM. All rights reserved.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def show_upload_page(llm_model, test_mode, tts_voice, narration_style):
    """Show file upload and processing page."""
    
    # Tabs for upload or load
    tab1, tab2 = st.tabs(["Upload New", "Load Saved"])
    
    with tab1:
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
            if st.button("Generate Presentation", type="primary", width="stretch"):
                process_presentation(
                    uploaded_file,
                    additional_context,
                    llm_model,
                    test_mode,
                    tts_voice,
                    narration_style
                )
    
    with tab2:
        st.header("Load Saved Presentation")
        
        # Get list of saved presentations
        saved_presentations = get_saved_presentations(Config.DATA_DIR)
        
        if not saved_presentations:
            st.info("No saved presentations found. Process a presentation first to save it.")
        else:
            st.write(f"Found {len(saved_presentations)} saved presentation(s)")
            
            # Display presentations in a table-like format
            for idx, pres in enumerate(saved_presentations):
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        st.write(f"**{pres.get('filename', 'Unknown')}**")
                        st.caption(f"Slides: {pres.get('num_slides', 0)} | Model: {pres.get('llm_model', 'N/A')}")
                    
                    with col2:
                        timestamp_str = pres.get('timestamp', '')
                        if timestamp_str:
                            # Format timestamp for display
                            from datetime import datetime
                            try:
                                dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                                st.caption(dt.strftime("%Y-%m-%d %H:%M"))
                            except:
                                st.caption(timestamp_str)
                    
                    with col3:
                        if st.button("Load", key=f"load_{idx}", width="stretch"):
                            load_saved_presentation(pres.get('timestamp'))
                    
                    st.divider()


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
        parser = SlideParser(use_vision=True)
        slides = parser.parse(file_path)

        st.success(f"Parsed {len(slides)} slides")

        # Generate narrations
        st.info("Generating narrations...")
        narration_gen = NarrationGenerator(provider="openai", model=llm_model)
        narrations = narration_gen.generate_narration(
            slides,
            context=context if context else None,
            style=narration_style,
            mode="continuous"
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
        st.session_state.llm_model = llm_model
        st.session_state.test_mode = test_mode
        st.session_state.timestamp = timestamp

        # Save metadata
        metadata = {
            "timestamp": timestamp,
            "filename": filename,
            "num_slides": len(slides),
            "llm_model": llm_model,
            "tts_voice": tts_voice,
            "narration_style": narration_style,
            "test_mode": test_mode
        }
        
        # Save complete presentation data
        save_presentation_data(
            timestamp=timestamp,
            slides=slides,
            narrations=narrations,
            audio_segments=audio_segments,
            metadata=metadata,
            base_dir=Config.DATA_DIR
        )

        st.rerun()


def load_saved_presentation(timestamp: str):
    """Load a previously saved presentation."""
    with st.spinner("Loading presentation..."):
        try:
            # Load presentation data
            data = load_presentation_data(timestamp, Config.DATA_DIR)
            
            # Update session state
            st.session_state.slides = data['slides']
            st.session_state.narrations = data['narrations']
            st.session_state.audio_segments = data['audio_segments']
            st.session_state.presentation_loaded = True
            st.session_state.current_slide_idx = 0
            st.session_state.timestamp = timestamp
            
            # Load metadata into session state
            metadata = data['metadata']
            st.session_state.llm_model = metadata.get('llm_model', 'gpt-4o-mini')
            st.session_state.test_mode = metadata.get('test_mode', True)
            
            st.success(f"Loaded presentation: {metadata.get('filename', 'Unknown')}")
            st.rerun()
            
        except Exception as e:
            st.error(f"Failed to load presentation: {e}")


def show_presentation_page():
    """Show presentation viewer."""

    slides = st.session_state.slides
    narrations = st.session_state.narrations
    current_idx = st.session_state.current_slide_idx
    
    # Check if we need to advance slide (set by JavaScript polling)
    if st.session_state.advance_slide:
        st.write("DEBUG: Advancing slide via session state")  # Debug line
        st.session_state.advance_slide = False
        # Advance to next slide (like clicking Next button)
        if current_idx < len(slides) - 1:
            st.session_state.current_slide_idx += 1
            st.session_state.audio_finished = False
            st.rerun()
        else:
            # End of presentation
            st.success("✅ Presentation complete!")
    
    # Clear audio position only when slide changes (not on every render)
    slide_changed = st.session_state.previous_slide_idx != current_idx
    if slide_changed:
        st.session_state.previous_slide_idx = current_idx
        clear_flag_html = f"""
        <script>
            console.log('Slide changed to {current_idx}, clearing localStorage flags');
            localStorage.removeItem('presentlm_audio_finished');
            localStorage.removeItem('presentlm_audio_position_slide_{current_idx}');
        </script>
        """
        components.html(clear_flag_html, height=0)
    
    # Show save status
    if 'timestamp' in st.session_state:
        st.success(f"Presentation saved and can be reloaded later (ID: {st.session_state.timestamp})")

    # Top controls
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 2])

    with col1:
        if st.button("Previous", ):
            if current_idx > 0:
                st.session_state.current_slide_idx -= 1
                st.session_state.audio_finished = False
                st.rerun()

    with col2:
        if st.button("Next"):
            if current_idx < len(slides) - 1:
                st.session_state.current_slide_idx += 1
                st.session_state.audio_finished = False
                st.rerun()

    with col3:
        st.write(f"Slide {current_idx + 1}/{len(slides)}")
    
    with col4:
        # Display slide counter
        st.write(f"Slide {current_idx + 1}/{len(slides)}")
    
    with col5:
        col5a, col5b = st.columns(2)
        with col5a:
            if st.button("New Presentation", width="stretch"):
                # Reset all session state
                st.session_state.presentation_loaded = False
                st.session_state.is_paused = False
                st.session_state.current_question = None
                st.session_state.current_answer = None
                st.session_state.waiting_for_feedback = False
                st.rerun()
        
        with col5b:
            # Export narrations as text file
            export_text = generate_narration_export(narrations)
            st.download_button(
                label="Download Narrations",
                data=export_text,
                file_name=f"narrations_{st.session_state.get('timestamp', 'export')}.txt",
                mime="text/plain",
                width="stretch"
            )

    # Current slide display
    current_slide = slides[current_idx]
    current_narration = narrations[current_idx]

    st.divider()

    # Two columns: slide content and controls
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader(f"Slide {current_slide.slide_number}: {current_slide.title}")

        # Slide content
        if current_slide.image_data:
            st.image(
                BytesIO(current_slide.image_data),
                width="stretch"
            )
        else:
            st.markdown(current_slide.content)

        if current_slide.notes:
                with st.expander("Speaker Notes"):
                    st.markdown(current_slide.notes)

        # Narration
        st.subheader("Narration")
        st.write(current_narration.narration_text)

        # Audio player with auto-play and completion detection
        if hasattr(st.session_state, 'audio_segments') and st.session_state.audio_segments:
            audio_segment = st.session_state.audio_segments[current_idx]
            if audio_segment.audio_path.exists():
                # Determine if audio should autoplay
                should_autoplay = not (st.session_state.is_paused or st.session_state.waiting_for_feedback or st.session_state.asking_question)
                autoplay_attr = "autoplay" if should_autoplay else ""
                
                # Read audio file and encode as base64
                with open(audio_segment.audio_path, 'rb') as audio_file:
                    audio_bytes = audio_file.read()
                    audio_base64 = base64.b64encode(audio_bytes).decode()
                
                # Custom HTML5 audio player with localStorage position tracking
                audio_html = f"""
                <audio id="presentlm-audio-{current_idx}" controls {autoplay_attr} style="width: 100%;">
                    <source src="data:audio/mpeg;base64,{audio_base64}" type="audio/mpeg">
                    Your browser does not support the audio element.
                </audio>
                <div id="debug-info" style="font-size: 12px; color: #666; margin-top: 5px;">Position: 0.0s</div>
                <script>
                    (function() {{
                        const audio = document.getElementById('presentlm-audio-{current_idx}');
                        const debugInfo = document.getElementById('debug-info');
                        const slideKey = 'presentlm_audio_position_slide_{current_idx}';
                        const finishedKey = 'presentlm_audio_finished';
                        
                        // Load saved position from localStorage
                        audio.addEventListener('loadedmetadata', function() {{
                            const savedPosition = localStorage.getItem(slideKey);
                            if (savedPosition && !isNaN(parseFloat(savedPosition))) {{
                                const position = parseFloat(savedPosition);
                                audio.currentTime = position;
                                debugInfo.textContent = 'Position: ' + position.toFixed(1) + 's (resumed)';
                            }}
                        }});
                        
                        // Save position every 1 second while playing
                        setInterval(function() {{
                            if (!audio.paused && !audio.ended) {{
                                localStorage.setItem(slideKey, audio.currentTime.toString());
                                debugInfo.textContent = 'Position: ' + audio.currentTime.toFixed(1) + 's (playing)';
                            }}
                        }}, 1000);
                        
                        // Save position on pause
                        audio.addEventListener('pause', function() {{
                            localStorage.setItem(slideKey, audio.currentTime.toString());
                            debugInfo.textContent = 'Position: ' + audio.currentTime.toFixed(1) + 's (paused)';
                        }});
                        
                        // When audio ends, set flag in localStorage
                        audio.addEventListener('ended', function() {{
                            console.log('Audio ended event fired!');
                            debugInfo.textContent = 'Audio finished! Signaling...';
                            localStorage.removeItem(slideKey);
                            localStorage.setItem(finishedKey, 'true');
                            console.log('Set localStorage flag:', localStorage.getItem(finishedKey));
                        }});
                    }})();
                </script>
                """
                components.html(audio_html, height=90)
                
                # Show pause status
                if st.session_state.is_paused or st.session_state.waiting_for_feedback or st.session_state.asking_question:
                    st.info("⏸️ Audio paused - Will resume from current position")
        elif st.session_state.get('test_mode', True):
            st.info("Test mode: Audio generation skipped. Enable TTS by disabling Test Mode checkbox")

    with col_right:
        st.subheader("Ask Questions")
        
        # If waiting for feedback on previous answer
        if st.session_state.waiting_for_feedback:
            st.markdown(f"**Q:** {st.session_state.current_question}")
            st.markdown(f"**A:** {st.session_state.current_answer}")
            
            st.divider()
            st.markdown("**Was this answer helpful?**")
            
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("Yes, Continue", type="primary", width="stretch"):
                    # Resume auto-advance and audio from saved position
                    st.session_state.is_paused = False
                    st.session_state.waiting_for_feedback = False
                    st.session_state.asking_question = False
                    st.session_state.current_question = None
                    st.session_state.current_answer = None
                    st.success("Resuming presentation...")
                    st.rerun()
            
            with col_no:
                if st.button("No, Ask Again", width="stretch"):
                    # Keep audio paused, allow follow-up question
                    st.session_state.waiting_for_feedback = False
                    st.session_state.current_answer = None
                    st.rerun()
        
        elif st.session_state.asking_question:
            # Question input UI (audio is already paused)
            st.info("⏸️ Presentation paused for Q&A")
            
            question_mode = st.radio(
                "Input method:",
                ["Text", "Audio"],
                horizontal=True
            )
            
            question_text = None
            
            if question_mode == "Text":
                question_text = st.text_input("Type your question:", key="text_question")
                ask_button = st.button("Submit Question", type="primary", width="stretch")
            else:
                st.info("Record your question:")
                audio_bytes = st.audio_input("Record question")
                
                if audio_bytes:
                    with st.spinner("Transcribing audio..."):
                        try:
                            # Initialize STT engine
                            stt = STTEngine(provider="openai")
                            question_text = stt.transcribe(audio_bytes.read())
                            st.success(f"Transcribed: {question_text}")
                            ask_button = True
                        except Exception as e:
                            st.error(f"Transcription failed: {e}")
                            ask_button = False
                else:
                    ask_button = False
            
            # Cancel button
            if st.button("Cancel", width="stretch"):
                st.session_state.asking_question = False
                st.session_state.is_paused = False
                st.rerun()
            
            # Process question
            if ask_button and question_text and question_text.strip():
                st.session_state.current_question = question_text
                
                with st.spinner("Generating answer..."):
                    try:
                        # Initialize question handler
                        question_handler = QuestionHandler(
                            provider="openai",
                            model=st.session_state.get('llm_model', 'gpt-4o-mini')
                        )
                        
                        # Get answer
                        answer = question_handler.answer_question(
                            question=question_text,
                            current_slide=slides[current_idx],
                            current_narration=narrations[current_idx],
                            all_slides=slides,
                            additional_context=None
                        )
                        
                        st.session_state.current_answer = answer
                        st.session_state.waiting_for_feedback = True
                        st.session_state.asking_question = False
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Failed to generate answer: {e}")
                        st.session_state.asking_question = False
                        st.session_state.is_paused = False
        
        else:
            # Show "Ask a Question" button when not in Q&A mode
            if st.button("❓ Ask a Question", type="primary", width="stretch"):
                # Pause presentation and audio
                st.session_state.is_paused = True
                st.session_state.asking_question = True
                st.rerun()
        
        st.divider()

        # Slide navigator
        st.subheader("Slide Navigator")
        for idx, slide in enumerate(slides):
            if st.button(
                f"{idx + 1}. {slide.title[:30]}...",
                key=f"nav_{idx}",
                width="stretch"
            ):
                st.session_state.current_slide_idx = idx
                st.session_state.audio_finished = False
                st.rerun()
    
    # Auto-advance polling (only when audio is playing)
    if hasattr(st.session_state, 'audio_segments') and st.session_state.audio_segments:
        if not st.session_state.waiting_for_feedback and not st.session_state.is_paused and not st.session_state.asking_question:
            # Create a hidden button that JavaScript will click when audio finishes
            auto_advance_clicked = st.button(
                "auto_advance_hidden",
                key=f"auto_advance_{current_idx}",
                disabled=False,
                type="secondary"
            )
            
            # Hide the button with CSS and add polling script
            components.html(
                f"""
                <style>
                    button[kind="secondary"] {{
                        display: none !important;
                    }}
                </style>
                <script>
                    (function() {{
                        console.log('Polling script started...');
                        
                        function checkAudioFinished() {{
                            const audioFinished = localStorage.getItem('presentlm_audio_finished');
                            console.log('Checking audio finished flag:', audioFinished);
                            
                            if (audioFinished === 'true') {{
                                console.log('Audio finished! Clicking advance button...');
                                localStorage.removeItem('presentlm_audio_finished');
                                
                                // Find and click the auto-advance button
                                const buttons = window.parent.document.querySelectorAll('button');
                                for (let btn of buttons) {{
                                    if (btn.textContent.includes('auto_advance_hidden')) {{
                                        console.log('Found button, clicking...');
                                        btn.click();
                                        return;
                                    }}
                                }}
                                console.log('Button not found!');
                            }}
                        }}
                        
                        // Check every 500ms
                        setInterval(checkAudioFinished, 500);
                        checkAudioFinished(); // Check immediately
                    }})();
                </script>
                """,
                height=0
            )
            
            # If button was clicked (by user or by JavaScript), advance the slide
            if auto_advance_clicked:
                st.write("DEBUG: Auto-advance triggered!")  # Debug line
                if current_idx < len(slides) - 1:
                    st.session_state.current_slide_idx += 1
                    st.session_state.audio_finished = False
                    st.rerun()
                else:
                    st.success("✅ Presentation complete!")


def generate_narration_export(narrations) -> str:
    """Generate a text export of all narrations."""
    export_lines = []
    export_lines.append("=" * 80)
    export_lines.append("PRESENTATION NARRATIONS")
    export_lines.append("=" * 80)
    export_lines.append("")
    
    for narration in narrations:
        export_lines.append(f"Slide {narration.slide_number}")
        export_lines.append("-" * 80)
        export_lines.append(narration.narration_text)
        export_lines.append("")
        export_lines.append(f"Estimated duration: {narration.estimated_duration:.1f} seconds")
        export_lines.append("")
        export_lines.append("")
    
    total_duration = sum(n.estimated_duration for n in narrations)
    export_lines.append("=" * 80)
    export_lines.append(f"Total slides: {len(narrations)}")
    export_lines.append(f"Total estimated duration: {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")
    export_lines.append("=" * 80)
    
    return "\n".join(export_lines)


if __name__ == "__main__":
    main()

