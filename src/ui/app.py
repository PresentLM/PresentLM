"""
PresentLM - Streamlit UI
Interactive presentation viewer with AI narration and Q&A.
"""

import base64
import sys
import time
import threading
from io import BytesIO
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Thread-safe storage for audio generation progress (not used anymore, using files instead)
_audio_generation_lock = threading.Lock()
_audio_generation_data = {}

def get_audio_progress_file(timestamp: str) -> Path:
    """Get the path to the audio progress file for a session."""
    return Config.DATA_DIR / f"{timestamp}_audio_progress.json"

def save_audio_progress(timestamp: str, ready: list, complete: bool):
    """Save audio generation progress to disk."""
    progress_file = get_audio_progress_file(timestamp)
    save_json({
        'ready': ready,
        'complete': complete
    }, progress_file)
    print(f"DEBUG FILE: Saved progress to {progress_file}, ready={ready}, complete={complete}")

def load_audio_progress(timestamp: str):
    """Load audio generation progress from disk."""
    progress_file = get_audio_progress_file(timestamp)
    print(f"DEBUG FILE: Trying to load from {progress_file}, exists={progress_file.exists()}")
    if progress_file.exists():
        data = load_json(progress_file)
        print(f"DEBUG FILE: Loaded data: {data}")
        return data
    print(f"DEBUG FILE: File does not exist")
    return None

from src.core import (
    NarrationGenerator,
    QuestionHandler,
    SlideParser,
    STTEngine,
    TTSEngine,
)
from src.utils import (
    Config,
    get_benchmark_tracker,
    get_saved_presentations,
    get_timestamp,
    load_presentation_data,
    reset_benchmark_tracker,
    sanitize_filename,
    save_presentation_data,
    save_json,
    load_json,
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
if 'audio_ready' not in st.session_state:
    st.session_state.audio_ready = []
if 'audio_generation_complete' not in st.session_state:
    st.session_state.audio_generation_complete = False
if 'generating_audio' not in st.session_state:
    st.session_state.generating_audio = False
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
if 'answer_audio_path' not in st.session_state:
    st.session_state.answer_audio_path = None
if 'answer_audio_finished' not in st.session_state:
    st.session_state.answer_audio_finished = False

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


    # Main content area
    if not st.session_state.presentation_loaded:
        show_upload_page()
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


def show_upload_page():
    """Show file upload and processing page."""
    st.markdown(''' <style>
    /* Hide default Streamlit elements */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        </style> ''', unsafe_allow_html=True)
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

        narration_style = st.selectbox(
            "Narration Style",
            ["educational", "professional", "casual"]
        )

        if uploaded_file:
            if st.button("Generate Presentation", type="primary", width="stretch"):
                process_presentation(
                    uploaded_file,
                    additional_context,
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
    narration_style,
    llm_model='gpt-4o-mini',
    test_mode=False,
    tts_voice='alloy',

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
        # Reset and get benchmark tracker
        reset_benchmark_tracker()
        benchmark = get_benchmark_tracker()
        
        # Save uploaded file
        timestamp = get_timestamp()
        filename = sanitize_filename(uploaded_file.name)
        file_path = Config.SLIDES_DIR / f"{timestamp}_{filename}"

        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Parse slides
        print("Parsing slides...")
        parser = SlideParser(use_vision=True)
        slides = parser.parse(file_path)

        print(f"Parsed {len(slides)} slides")

        # Generate narrations
        print("Generating narrations...")
        narration_gen = NarrationGenerator(provider="openai", model=llm_model)
        narrations = narration_gen.generate_narration(
            slides,
            context=context if context else None,
            style=narration_style,
            mode="continuous"
        )

        print(f"Generated {len(narrations)} narrations")

        # Save to session state first (before audio generation)
        st.session_state.slides = slides
        st.session_state.narrations = narrations
        st.session_state.audio_segments = [None] * len(narrations)  # Placeholder list
        st.session_state.audio_ready = [False] * len(narrations)
        st.session_state.llm_model = llm_model
        st.session_state.test_mode = test_mode
        st.session_state.timestamp = timestamp
        st.session_state.audio_generation_complete = test_mode  # Complete immediately in test mode

        # Generate audio in background (skip in test mode to save tokens)
        if test_mode:
            print("Test mode enabled - Skipping TTS generation to save tokens")
            # Mark all slides as ready in test mode
            st.session_state.audio_ready = [True] * len(narrations)
            st.session_state.presentation_loaded = True
        else:
            print("Starting audio generation in background...")
            st.session_state.generating_audio = True

            # Initialize progress file on disk
            save_audio_progress(timestamp, [False] * len(narrations), False)

            # Start background thread for audio generation
            def generate_audio_background():
                """Generate audio for all slides in background."""
                print(f"DEBUG: Background thread started for {len(narrations)} slides")
                ready_flags = [False] * len(narrations)
                segments_list = [None] * len(narrations)

                try:
                    tts = TTSEngine(provider="openai", voice=tts_voice)

                    for idx, narration in enumerate(narrations):
                        print(f"DEBUG: Starting audio generation for slide {idx + 1}/{len(narrations)}")
                        try:
                            audio_path = Config.AUDIO_DIR / f"{timestamp}_slide_{narration.slide_number}.mp3"
                            segment = tts.generate_audio(narration.narration_text, audio_path)
                            segment.slide_number = narration.slide_number

                            # Store segment locally
                            segments_list[idx] = segment
                            ready_flags[idx] = True

                            # Save progress to disk
                            save_audio_progress(timestamp, ready_flags, False)
                            print(f"DEBUG: Marked slide {idx + 1} as ready in file")

                        except Exception as e:
                            print(f"Error generating audio for slide {idx + 1}: {e}")
                            ready_flags[idx] = False
                            save_audio_progress(timestamp, ready_flags, False)

                    # Mark as complete
                    save_audio_progress(timestamp, ready_flags, True)
                    print(f"DEBUG: All audio generation complete, marked as done in file")

                    # Also save audio segments data now that all are complete
                    audio_data = [seg.to_dict() for seg in segments_list if seg]
                    save_json({"audio_segments": audio_data}, Config.DATA_DIR / f"{timestamp}_audio.json")
                    print(f"DEBUG: Saved {len(audio_data)} audio segments to file")

                except Exception as e:
                    print(f"Fatal error in audio generation: {e}")
                    save_audio_progress(timestamp, ready_flags, True)

            audio_thread = threading.Thread(target=generate_audio_background, daemon=True)
            audio_thread.start()

            # Poll until first slide is ready (with timeout) - no UI messages, just wait
            max_wait = 60  # 60 seconds max wait
            waited = 0
            first_slide_ready = False
            while waited < max_wait:
                progress_data = load_audio_progress(timestamp)
                if progress_data and progress_data['ready'][0]:
                    # First slide ready
                    st.session_state.presentation_loaded = True
                    print("First slide ready! Starting presentation...")
                    first_slide_ready = True
                    break
                time.sleep(0.5)
                waited += 0.5

            if not first_slide_ready:
                st.error("Timeout waiting for first slide audio generation")
                st.session_state.generating_audio = False
                return

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
        
        # Save presentation data (audio segments will be saved as they're generated)
        # For now, save with empty audio segments list
        save_presentation_data(
            timestamp=timestamp,
            slides=slides,
            narrations=narrations,
            audio_segments=[],  # Will be populated as audio is generated
            metadata=metadata,
            base_dir=Config.DATA_DIR
        )

        # Save benchmark data
        benchmark_file = Config.DATA_DIR / f"benchmark_{timestamp}.json"
        benchmark.save_json(benchmark_file)

        # Print benchmark summary to console
        benchmark.print_summary()

        # Rerun to transition to presentation mode
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

            # Mark all audio as ready (since it's a saved presentation)
            st.session_state.audio_ready = [True] * len(data['slides'])
            st.session_state.audio_generation_complete = True
            st.session_state.generating_audio = False
            
            # Load metadata into session state
            metadata = data['metadata']
            st.session_state.llm_model = metadata.get('llm_model', 'gpt-4o-mini')
            st.session_state.test_mode = metadata.get('test_mode', True)
            
            # Load existing benchmark data if it exists, so Q&A interactions are appended to it
            benchmark = get_benchmark_tracker(session_id=timestamp)
            benchmark_file = Config.DATA_DIR / f"benchmark_{timestamp}.json"
            if benchmark_file.exists():
                try:
                    benchmark.load_json(benchmark_file)
                    st.info(f"✓ Loaded existing benchmarks")
                except Exception as e:
                    st.warning(f"Could not load existing benchmarks: {e}")
            
            st.success(f"Loaded presentation: {metadata.get('filename', 'Unknown')}")
            st.rerun()
            
        except Exception as e:
            st.error(f"Failed to load presentation: {e}")


def show_presentation_page():
    """Show presentation viewer with new clean UI design."""

    # Add custom CSS for compact toolbar and viewport-fitted layout
    st.markdown("""
    <style>
        /* Hide default Streamlit elements */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Optimize container padding */
        .block-container {
            padding-top: 0.5rem;
            padding-bottom: 0.5rem;
            padding-left: 1rem;
            padding-right: 1rem;
            max-width: 100%;
        }
        
        /* Reduce all vertical spacing */
        .element-container {
            margin-bottom: 0.25rem;
        }
        
        div[data-testid="stVerticalBlock"] > div {
            gap: 0.25rem;
        }
        
        /* Compact buttons */
        .stButton button {
            padding: 0.35rem 0.75rem;
            font-size: 0.875rem;
            height: 2.5rem;
        }
        
        /* Hide home button completely and remove its space */
        .st-key-home_button {
            display: none !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            visibility: hidden !important;
        }
        
        /* Compact selectbox */
        div[data-baseweb="select"] {
            margin-bottom: 0.25rem;
        }
        
        /* Compact expander */
        .streamlit-expanderHeader {
            font-size: 0.9rem;
            padding: 0.4rem 0.75rem;
            font-weight: 500;
        }
        
        .streamlit-expanderContent {
            padding: 0.5rem 0.75rem;
        }
        
        /* Optimize slide image to fit viewport */
        .stImage {
            max-height: calc(100vh - 320px);
            object-fit: contain;
        }
        
        .stImage img {
            max-height: calc(100vh - 320px);
            object-fit: contain;
        }
        
        /* Compact audio player */
        audio {
            height: 40px;
        }
        
        /* Compact horizontal dividers */
        hr {
            margin-top: 0.5rem;
            margin-bottom: 0.5rem;
        }
        
        /* Compact download button */
        .stDownloadButton button {
            padding: 0.35rem 0.75rem;
            font-size: 0.875rem;
            height: 2.5rem;
        }
        
        /* Reduce gap between columns */
        div[data-testid="column"] {
            padding: 0 0.25rem;
        }
    </style>
    """, unsafe_allow_html=True)

    # Update from progress file ONCE per render
    timestamp = st.session_state.get('timestamp')
    print(f"DEBUG: Checking for updates, timestamp={timestamp}, complete={st.session_state.get('audio_generation_complete', True)}")

    if timestamp and not st.session_state.get('audio_generation_complete', True):
        # Load progress from file
        progress_data = load_audio_progress(timestamp)

        if progress_data:
            ready_in_file = sum(progress_data['ready'])
            ready_in_session = sum(st.session_state.audio_ready)
            print(f"DEBUG: File has {ready_in_file} ready, Session has {ready_in_session} ready")

            # Update session state based on file
            has_updates = False
            for idx in range(len(progress_data['ready'])):
                if progress_data['ready'][idx] and not st.session_state.audio_ready[idx]:
                    print(f"DEBUG: Updating slide {idx} to ready")
                    # Load the audio segment from disk
                    audio_path = Config.AUDIO_DIR / f"{timestamp}_slide_{idx + 1}.mp3"
                    if audio_path.exists():
                        from src.core import AudioSegment
                        segment = AudioSegment(
                            audio_path=audio_path,
                            duration=0,
                            text="",
                            slide_number=idx + 1
                        )
                        st.session_state.audio_segments[idx] = segment
                        st.session_state.audio_ready[idx] = True
                        has_updates = True
                        print(f"DEBUG: Successfully loaded audio segment for slide {idx + 1}")

            # Check if complete
            if progress_data['complete'] and not st.session_state.audio_generation_complete:
                print(f"DEBUG: Marking generation as complete")
                st.session_state.audio_generation_complete = True
                st.session_state.generating_audio = False

                # Clean up progress file
                progress_file = get_audio_progress_file(timestamp)
                if progress_file.exists():
                    progress_file.unlink()
                    print(f"DEBUG: Cleaned up progress file")

                has_updates = True

    slides = st.session_state.slides
    narrations = st.session_state.narrations

    # Process any pending navigation actions FIRST, before reading current_idx
    # This ensures that when buttons are clicked, the navigation happens immediately

    # Check for auto-advance (from audio end)
    if st.session_state.get('advance_slide', False):
        st.session_state.advance_slide = False
        if st.session_state.current_slide_idx < len(slides) - 1:
            st.session_state.current_slide_idx += 1
            st.session_state.audio_finished = False
            # Update selectbox to match new slide
            st.session_state.slide_changed_externally = True
            print(f"DEBUG: Auto-advance triggered, moving to slide {st.session_state.current_slide_idx + 1}")
            st.rerun()

    # Check for navigation button clicks (these are set by on_click callbacks)
    if st.session_state.get('nav_next', False):
        st.session_state.nav_next = False
        if st.session_state.current_slide_idx < len(slides) - 1:
            st.session_state.current_slide_idx += 1
            st.session_state.audio_finished = False
            # Update selectbox to match new slide
            st.session_state.slide_changed_externally = True
            print(f"DEBUG: Next button, moving to slide {st.session_state.current_slide_idx + 1}")
            st.rerun()

    if st.session_state.get('nav_prev', False):
        st.session_state.nav_prev = False
        if st.session_state.current_slide_idx > 0:
            st.session_state.current_slide_idx -= 1
            st.session_state.audio_finished = False
            # Update selectbox to match new slide
            st.session_state.slide_changed_externally = True
            print(f"DEBUG: Previous button, moving to slide {st.session_state.current_slide_idx + 1}")
            st.rerun()

    # NOW read the current index (after all navigation is processed)
    current_idx = st.session_state.current_slide_idx

    # Clear audio position only when slide changes
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
    
    # Print save status to terminal only
    if 'timestamp' in st.session_state:
        print(f"Presentation saved and can be reloaded later (ID: {st.session_state.timestamp})")

    # Initialize Q&A panel state
    if 'qa_panel_open' not in st.session_state:
        st.session_state.qa_panel_open = False

    current_slide = slides[current_idx]
    current_narration = narrations[current_idx]

    # === 1. TOOLBAR: Logo icon and download button ===
    toolbar_col1, toolbar_col2, toolbar_col3 = st.columns([2, 5.7, 1])

    with toolbar_col1:
        # Hidden button for home navigation
        if st.button("home_hidden", key="home_button"):
            st.session_state.presentation_loaded = False
            st.session_state.is_paused = False
            st.session_state.current_question = None
            st.session_state.current_answer = None
            st.session_state.waiting_for_feedback = False
            st.session_state.qa_panel_open = False
            st.rerun()

        # Logo icon that triggers the hidden button
        components.html(f"""
        <div style="width:110px; height:40px; display: flex; align-items: center; margin: 0; padding: 0;">
            <img id="presentlm-home-icon"
                 src="data:image/png;base64,{get_base64_image('src/assets/PresentLM-logo.png')}"
                 style="width:100%; height:100%; object-fit: contain; cursor: pointer;"
                 alt="Home"
                 title="Back to Home"
            >
        </div>
        <script>
            (function() {{
                const icon = document.getElementById('presentlm-home-icon');
                if (icon) {{
                    icon.addEventListener('click', function() {{
                        // Find and click the hidden home button
                        const buttons = window.parent.document.querySelectorAll('button');
                        for (let btn of buttons) {{
                            const text = btn.textContent || '';
                            if (text.includes('home_hidden')) {{
                                btn.click();
                                return;
                            }}
                        }}
                    }});
                }}
            }})();
        </script>
        """, height=40)

    with toolbar_col3:
        # Export button
        export_text = generate_narration_export(narrations)
        st.download_button(
            label="📥 Download",
            data=export_text,
            file_name=f"narrations_{st.session_state.get('timestamp', 'export')}.txt",
            mime="text/plain",
            help="Download Narrations",
            use_container_width=True
        )

    # Show audio generation progress if still generating
    if not st.session_state.get('audio_generation_complete', True):
        ready_count = sum(st.session_state.audio_ready)
        total_count = len(st.session_state.audio_ready)
        progress_pct = ready_count / total_count if total_count > 0 else 0

        col_prog, col_refresh = st.columns([9, 1])
        with col_prog:
            st.progress(progress_pct, text=f"Audio generation: {ready_count}/{total_count} slides ready")
        with col_refresh:
            if st.button("🔄", key="refresh_progress", help="Refresh"):
                st.rerun()

        # Print debug info to terminal only
        print(f"DEBUG UI: Audio ready flags: {st.session_state.audio_ready}")
        print(f"DEBUG UI: Current slide: {current_idx + 1}")

    # === 2. SLIDE SELECTOR BAR ===
    # Create slide options for selectbox
    slide_options = []
    for idx, slide in enumerate(slides):
        audio_indicator = "🔊" if st.session_state.audio_ready[idx] else "⏳"
        slide_options.append(f"{audio_indicator} Slide {idx + 1}/{len(slides)}: {slide.title}")

    # Synchronize selectbox with current_idx
    # If slide changed externally (via buttons), update the selectbox value
    if st.session_state.get('slide_changed_externally', False):
        st.session_state.slide_selector_value = slide_options[current_idx]
        st.session_state.slide_changed_externally = False

    # Initialize selectbox value if not set
    if 'slide_selector_value' not in st.session_state:
        st.session_state.slide_selector_value = slide_options[current_idx]

    # Use on_change callback to handle slide selection
    def on_slide_select():
        """Handle slide selection from selectbox."""
        selected_text = st.session_state.slide_selector_value
        selected_idx = slide_options.index(selected_text)
        if selected_idx != st.session_state.current_slide_idx:
            if st.session_state.audio_ready[selected_idx]:
                st.session_state.current_slide_idx = selected_idx
                st.session_state.audio_finished = False

    st.selectbox(
        label="Navigate to slide:",
        options=slide_options,
        key="slide_selector_value",
        on_change=on_slide_select,
        label_visibility="collapsed"
    )


    # === 3. SLIDE DISPLAY WITH Q&A PANEL ===
    # Create columns: slide takes 3/4 if Q&A is open, full width otherwise
    if st.session_state.qa_panel_open:
        slide_col, qa_col = st.columns([3, 1])
    else:
        slide_col = st.container()
        qa_col = None

    with slide_col:
        # Q&A button in top right corner
        qa_button_col1, qa_button_col2 = st.columns([9, 1])
        with qa_button_col2:
            if st.button("❓", key="qa_toggle", help="Ask a Question"):
                st.session_state.qa_panel_open = not st.session_state.qa_panel_open
                if st.session_state.qa_panel_open:
                    st.session_state.is_paused = True
                    st.session_state.asking_question = True
                else:
                    st.session_state.is_paused = False
                    st.session_state.asking_question = False
                st.rerun()

        # Slide content
        if current_slide.image_data:
            st.image(
                BytesIO(current_slide.image_data),
                use_container_width=True
            )
        else:
            st.markdown(current_slide.content)

        # Speaker notes (if available)
        if current_slide.notes:
            with st.expander("📝 Speaker Notes"):
                st.markdown(current_slide.notes)

    # Q&A Panel (if open)
    if st.session_state.qa_panel_open and qa_col:
        with qa_col:
            st.markdown("### Ask a Question")

            # If waiting for feedback on previous answer
            if st.session_state.waiting_for_feedback:
                st.markdown(f"**Q:** {st.session_state.current_question}")
                st.markdown(f"**A:** {st.session_state.current_answer}")

                # Play answer audio if available and not in test mode
                if st.session_state.answer_audio_path and not st.session_state.get('test_mode', True):
                    if not st.session_state.answer_audio_finished:
                        with open(st.session_state.answer_audio_path, 'rb') as audio_file:
                            answer_audio_bytes = audio_file.read()
                            answer_audio_base64 = base64.b64encode(answer_audio_bytes).decode()

                        answer_audio_html = f"""
                        <div style="margin: 10px 0;">
                            <audio id="answer-audio" controls autoplay style="width: 100%;">
                                <source src="data:audio/mpeg;base64,{answer_audio_base64}" type="audio/mpeg">
                            </audio>
                        </div>
                        <script>
                            (function() {{
                                const audio = document.getElementById('answer-audio');
                                audio.addEventListener('ended', function() {{
                                    localStorage.setItem('answer_audio_finished', 'true');
                                }});
                            }})();
                        </script>
                        """
                        components.html(answer_audio_html, height=70)

                        answer_done_btn = st.button(
                            "answer_done_hidden",
                            key="answer_audio_done",
                            type="secondary"
                        )

                        components.html("""
                        <script>
                            (function() {
                                function checkAnswerFinished() {
                                    const finished = localStorage.getItem('answer_audio_finished');
                                    if (finished === 'true') {
                                        localStorage.removeItem('answer_audio_finished');
                                        const buttons = window.parent.document.querySelectorAll('button');
                                        for (let btn of buttons) {
                                            if (btn.textContent.includes('answer_done_hidden')) {
                                                btn.style.display = 'none';
                                                btn.click();
                                                return;
                                            }
                                        }
                                    }
                                }
                                setInterval(checkAnswerFinished, 500);
                            })();
                        </script>
                        """, height=0)

                        if answer_done_btn:
                            st.session_state.answer_audio_finished = True
                            st.rerun()
                else:
                    st.session_state.answer_audio_finished = True

                if st.session_state.answer_audio_finished:
                    st.divider()
                    st.markdown("**Was this helpful?**")

                    if st.button("✅ Yes", key="yes_helpful", width="stretch"):
                        st.session_state.is_paused = False
                        st.session_state.waiting_for_feedback = False
                        st.session_state.asking_question = False
                        st.session_state.current_question = None
                        st.session_state.current_answer = None
                        st.session_state.answer_audio_path = None
                        st.session_state.answer_audio_finished = False
                        st.session_state.qa_panel_open = False
                        st.rerun()

                    if st.button("❌ No", key="no_helpful", width="stretch"):
                        st.session_state.waiting_for_feedback = False
                        st.session_state.current_answer = None
                        st.session_state.answer_audio_path = None
                        st.session_state.answer_audio_finished = False
                        st.rerun()

            elif st.session_state.asking_question:
                question_mode = st.radio(
                    "Input method:",
                    ["Text", "Audio"],
                    horizontal=True,
                    key="qa_input_mode"
                )

                question_text = None

                if question_mode == "Text":
                    question_text = st.text_area("Your question:", key="text_question", height=100)
                    ask_button = st.button("Submit", type="primary", width="stretch")
                else:
                    st.info("🎤 Record:")
                    audio_bytes = st.audio_input("Record question")

                    if audio_bytes:
                        with st.spinner("Transcribing..."):
                            try:
                                stt = STTEngine(provider="openai")
                                question_text = stt.transcribe(audio_bytes.read())
                                st.success(f"📝 {question_text}")
                                ask_button = True
                            except Exception as e:
                                st.error(f"Error: {e}")
                                ask_button = False
                    else:
                        ask_button = False

                if st.button("Cancel", width="stretch"):
                    st.session_state.asking_question = False
                    st.session_state.is_paused = False
                    st.session_state.qa_panel_open = False
                    st.rerun()

                if ask_button and question_text and question_text.strip():
                    st.session_state.current_question = question_text

                    with st.spinner("Generating answer..."):
                        try:
                            question_handler = QuestionHandler(
                                provider="openai",
                                model=st.session_state.get('llm_model', 'gpt-4o-mini')
                            )

                            answer = question_handler.answer_question(
                                question=question_text,
                                current_slide=slides[current_idx],
                                current_narration=narrations[current_idx],
                                all_slides=slides,
                                additional_context=None
                            )

                            st.session_state.current_answer = answer

                            if not st.session_state.get('test_mode', True):
                                try:
                                    tts = TTSEngine(
                                        provider="openai",
                                        voice=st.session_state.get('tts_voice', 'alloy')
                                    )

                                    import tempfile
                                    answer_audio_path = Path(tempfile.gettempdir()) / f"presentlm_answer_{get_timestamp()}.mp3"
                                    tts.generate_audio(answer, answer_audio_path)
                                    st.session_state.answer_audio_path = answer_audio_path
                                except Exception as e:
                                    st.warning(f"Could not generate audio: {e}")
                                    st.session_state.answer_audio_path = None
                            else:
                                st.session_state.answer_audio_path = None

                            benchmark = get_benchmark_tracker()
                            if 'timestamp' in st.session_state:
                                benchmark_file = Config.DATA_DIR / f"benchmark_{st.session_state.timestamp}.json"
                                benchmark.save_json(benchmark_file)

                            st.session_state.waiting_for_feedback = True
                            st.session_state.asking_question = False
                            st.session_state.answer_audio_finished = False
                            st.rerun()

                        except Exception as e:
                            st.error(f"Failed: {e}")
                            st.session_state.asking_question = False
                            st.session_state.is_paused = False

    # === 4. CONTROLS BAR: Previous | Audio Player | Next ===
    st.markdown("---")

    control_col1, control_col2, control_col3 = st.columns([1, 8, 1])

    with control_col1:
        # Previous button (only active if not first slide)
        if current_idx > 0:
            st.button(
                "⬅️ Previous",
                key="prev_slide",
                use_container_width=True,
                on_click=lambda: st.session_state.update({'nav_prev': True})
            )
        else:
            st.button("⬅️ Previous", key="prev_slide_disabled", disabled=True, use_container_width=True)

    with control_col2:
        # Audio player
        if hasattr(st.session_state, 'audio_segments') and st.session_state.audio_segments:
            audio_segment = st.session_state.audio_segments[current_idx]
            if audio_segment and audio_segment.audio_path.exists():
                should_autoplay = not (st.session_state.is_paused or st.session_state.waiting_for_feedback or st.session_state.asking_question)
                autoplay_attr = "autoplay" if should_autoplay else ""

                with open(audio_segment.audio_path, 'rb') as audio_file:
                    audio_bytes = audio_file.read()
                    audio_base64 = base64.b64encode(audio_bytes).decode()

                audio_html = f"""
                <audio id="presentlm-audio-{current_idx}" controls {autoplay_attr} style="width: 100%;">
                    <source src="data:audio/mpeg;base64,{audio_base64}" type="audio/mpeg">
                </audio>
                <script>
                    (function() {{
                        const audio = document.getElementById('presentlm-audio-{current_idx}');
                        const slideKey = 'presentlm_audio_position_slide_{current_idx}';
                        const finishedKey = 'presentlm_audio_finished';
                        
                        audio.addEventListener('loadedmetadata', function() {{
                            const savedPosition = localStorage.getItem(slideKey);
                            if (savedPosition && !isNaN(parseFloat(savedPosition))) {{
                                audio.currentTime = parseFloat(savedPosition);
                                console.log('Audio position restored to:', savedPosition + 's');
                            }}
                        }});
                        
                        setInterval(function() {{
                            if (!audio.paused && !audio.ended) {{
                                localStorage.setItem(slideKey, audio.currentTime.toString());
                            }}
                        }}, 1000);
                        
                        audio.addEventListener('pause', function() {{
                            localStorage.setItem(slideKey, audio.currentTime.toString());
                        }});
                        
                        audio.addEventListener('ended', function() {{
                            console.log('Audio ended!');
                            localStorage.removeItem(slideKey);
                            localStorage.setItem(finishedKey, 'true');
                        }});
                    }})();
                </script>
                """
                components.html(audio_html, height=60)
        elif st.session_state.get('test_mode', True):
            st.info("🔇 Test mode: Audio generation skipped")

    with control_col3:
        # Next button (only active if not last slide)
        if current_idx < len(slides) - 1:
            if st.session_state.audio_ready[current_idx + 1]:
                st.button(
                    "Next ➡️",
                    key="next_slide",
                    use_container_width=True,
                    on_click=lambda: st.session_state.update({'nav_next': True})
                )
            else:
                st.button("Next ➡️", key="next_slide_waiting", disabled=True, use_container_width=True, help="⏳ Audio generating...")
        else:
            st.button("Next ➡️", key="next_slide_disabled", disabled=True, use_container_width=True)

    # === 5. NARRATION EXPANDER ===
    with st.expander("📄 Narration", expanded=False):
        st.markdown(current_narration.narration_text)

    # Auto-advance polling
    if hasattr(st.session_state, 'audio_segments') and st.session_state.audio_segments:
        if not st.session_state.waiting_for_feedback and not st.session_state.is_paused and not st.session_state.asking_question:
            if current_idx < len(slides) - 1:
                auto_advance_clicked = st.button(
                    "auto_advance_hidden",
                    key=f"auto_advance_{current_idx}",
                    disabled=False,
                    type="secondary",
                    on_click=lambda: st.session_state.update({'advance_slide': True})
                )

                components.html("""
                <script>
                    (function() {
                        function hideHiddenButtons() {
                            const buttons = window.parent.document.querySelectorAll('button');
                            buttons.forEach(btn => {
                                const text = btn.textContent || '';
                                if (text.includes('_hidden')) {
                                    btn.style.display = 'none';
                                    btn.style.visibility = 'hidden';
                                    btn.style.position = 'absolute';
                                    btn.style.left = '-9999px';
                                }
                            });
                        }
                        hideHiddenButtons();
                        setInterval(hideHiddenButtons, 100);
                    })();
                </script>
                """, height=0)

                components.html(
                    f"""
                    <script>
                        (function() {{
                            function checkAudioFinished() {{
                                const audioFinished = localStorage.getItem('presentlm_audio_finished');
                                if (audioFinished === 'true') {{
                                    console.log('Audio finished flag detected, clicking auto-advance button...');
                                    localStorage.removeItem('presentlm_audio_finished');
                                    const buttons = window.parent.document.querySelectorAll('button');
                                    for (let btn of buttons) {{
                                        const text = btn.textContent || '';
                                        if (text.includes('auto_advance_hidden')) {{
                                            console.log('Found auto-advance button, clicking now');
                                            btn.click();
                                            return;
                                        }}
                                    }}
                                }}
                            }}
                            setInterval(checkAudioFinished, 500);
                        }})();
                    </script>
                    """,
                    height=0
                )



def get_base64_image(image_path: str) -> str:
    """Convert image to base64 string."""
    try:
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except:
        return ""


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

