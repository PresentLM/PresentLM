"""
PresentLM - Streamlit UI
Interactive presentation viewer with AI narration and Q&A.
"""

import base64
import json
import sys
import time
import threading
from io import BytesIO
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas
from PIL import Image as PILImage

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

def load_audio_progress(timestamp: str):
    """Load audio generation progress from disk."""
    progress_file = get_audio_progress_file(timestamp)
    if progress_file.exists():
        try:
            data = load_json(progress_file)
            return data
        except (json.JSONDecodeError, ValueError) as e:
            # Silently delete corrupted files
            progress_file.unlink()
            return None
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

# Pre-load Qwen TTS if selected (to avoid import time counting as generation time)
if 'qwen_preloaded' not in st.session_state:
    st.session_state.qwen_preloaded = False

if Config.TTS_PROVIDER == "qwen" and not st.session_state.qwen_preloaded:
    with st.spinner("Loading Qwen3-TTS model (first time only)..."):
        try:
            print("Pre-loading Qwen3-TTS model at app startup...")
            # Create a dummy TTS engine to trigger model loading
            _dummy_tts = TTSEngine()
            st.session_state.qwen_preloaded = True
            print("✅ Qwen3-TTS model pre-loaded successfully")
        except Exception as e:
            print(f"Warning: Could not pre-load Qwen3-TTS: {e}")
            # Don't fail the app, just log the warning

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
    else:
        show_presentation_page()


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
            placeholder="Example: 'Explain to a 10 year old child with no technical knowledge' or 'Use simple language for beginners' or 'Include real-world examples'",
            help="Specify target audience, complexity level, or presentation approach. This helps tailor the narration style and language.",
            height=150
        )

        if uploaded_file:
            if st.button("Generate Presentation", type="primary", width="stretch"):
                process_presentation(
                    uploaded_file,
                    additional_context
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
    llm_model='gpt-4o-mini',
    test_mode=False,
    tts_voice=None,  # Will use Config.TTS_VOICE if None

):
    """Process uploaded presentation."""

    # Use Config values if not specified
    if tts_voice is None:
        tts_voice = Config.TTS_VOICE

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
        # Generate a session timestamp first (used for file names and benchmark session id)
        timestamp = get_timestamp()

        # Reset and get benchmark tracker
        reset_benchmark_tracker()
        benchmark = get_benchmark_tracker(session_id=timestamp)
        benchmark_file = Config.DATA_DIR / f"benchmark_{timestamp}.json"
        benchmark.configure_persistence(benchmark_file, auto_save=True)

        # Save uploaded file
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
                    tts = TTSEngine(voice=tts_voice)  # Uses Config.TTS_PROVIDER

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

            # Poll until first slide is ready (no timeout - wait indefinitely)
            first_slide_ready = False
            while not first_slide_ready:
                progress_data = load_audio_progress(timestamp)
                if progress_data and progress_data['ready'][0]:
                    # First slide ready
                    st.session_state.presentation_loaded = True
                    print("First slide ready! Starting presentation...")
                    first_slide_ready = True
                    break
                time.sleep(0.5)
            time.sleep(1)
        # Save metadata
        metadata = {
            "timestamp": timestamp,
            "filename": filename,
            "num_slides": len(slides),
            "llm_model": llm_model,
            "tts_voice": tts_voice,
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

        # Save benchmark data (will already be kept up-to-date via auto-save)
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
            benchmark.configure_persistence(benchmark_file, auto_save=True)
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


@st.cache_data
def get_slide_image(slide_number: int, image_data: bytes) -> bytes:
    """Cache slide images to avoid reprocessing on every rerender.
    Also optimizes images for faster display.

    Args:
        slide_number: Unique identifier for the slide
        image_data: The raw image bytes

    Returns:
        Optimized image bytes ready for display
    """
    # For JPEG images from PDF, return as-is (already optimized)
    # For other formats, could add additional optimization here
    return image_data


def show_presentation_page():
    """Show presentation viewer with new clean UI design."""

    # Add custom CSS for compact toolbar and viewport-fitted layout
    st.markdown("""
    <style>
        /* Hide default Streamlit elements */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Make body fit viewport exactly */
        html, body {
            height: 100vh;
            overflow: hidden !important;
        }
        
        [data-testid="stAppViewContainer"] {
            height: 100vh;
            overflow-y: auto;
            overflow-x: hidden;
        }
        
        /* Main container - constrain to viewport */
        .block-container {
            padding: 0.2rem 0.4rem;
            max-width: 100%;
            min-height: 100vh;
            max-height: 100vh;
        }
        
        /* Reduce all vertical spacing */
        .element-container {
            margin-bottom: 0.08rem;
        }
        
        div[data-testid="stVerticalBlock"] > div {
            gap: 0.08rem;
        }
        
        /* Compact buttons */
        .stButton button {
            padding: 0.15rem 0.35rem;
            font-size: 0.75rem;
            height: 1.8rem;
            line-height: 1;
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
            margin-bottom: 0.05rem;
            min-height: 28px;
        }
        
        div[data-baseweb="select"] > div {
            min-height: 28px;
            font-size: 0.75rem;
        }
        
        /* Compact expander */
        .streamlit-expanderHeader {
            font-size: 0.7rem;
            padding: 0.15rem 0.35rem;
            font-weight: 500;
            min-height: 26px;
        }
        
        .streamlit-expanderContent {
            padding: 0.25rem 0.4rem;
            max-height: 8vh;
            overflow-y: auto;
            font-size: 0.7rem;
            line-height: 1.3;
        }
        
        /* Slide image - use viewport-relative sizing */
        .stImage {
            max-height: 60vh;
            min-height: 200px;
            object-fit: contain;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0.1rem 0;
        }
        
        .stImage img {
            max-height: 50vh;
            height: auto;
            width: auto;
            max-width: 100%;
            object-fit: contain;
        }
        
        /* Compact audio player */
        audio {
            height: 28px;
        }
        
        /* Compact horizontal dividers */
        hr {
            margin: 0.1rem 0;
            border-width: 0.5px;
        }
        
        /* Compact download button */
        .stDownloadButton button {
            padding: 0.15rem 0.35rem;
            font-size: 0.75rem;
            height: 1.8rem;
            line-height: 1;
        }
        
        /* Reduce gap between columns */
        div[data-testid="column"] {
            padding: 0 0.1rem;
        }
        
        /* Compact progress bar */
        .stProgress {
            height: 0.15rem;
        }
        
        /* Compact info/warning boxes */
        .stAlert {
            padding: 0.15rem 0.35rem;
            font-size: 0.7rem;
            line-height: 1.2;
        }
        
        /* Compact text areas and inputs */
        textarea {
            font-size: 0.75rem;
        }
        
        /* iframe components */
        iframe {
            margin: 0 !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # Update from progress file ONCE per render, but throttle to avoid excessive file I/O
    timestamp = st.session_state.get('timestamp')

    # Initialize last check time if not exists
    if 'last_progress_check' not in st.session_state:
        st.session_state.last_progress_check = 0

    current_time = time.time()
    should_check_progress = (current_time - st.session_state.last_progress_check) >= 2.0  # Check every 2 seconds

    if timestamp and not st.session_state.get('audio_generation_complete', True) and should_check_progress:
        st.session_state.last_progress_check = current_time

        # Load progress from file
        progress_data = load_audio_progress(timestamp)

        if progress_data:
            ready_in_file = sum(progress_data['ready'])
            ready_in_session = sum(st.session_state.audio_ready)

            # Update session state based on file
            has_updates = False
            for idx in range(len(progress_data['ready'])):
                if progress_data['ready'][idx] and not st.session_state.audio_ready[idx]:
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

            # Check if complete
            if progress_data['complete'] and not st.session_state.audio_generation_complete:
                st.session_state.audio_generation_complete = True
                st.session_state.generating_audio = False

                # Clean up progress file
                progress_file = get_audio_progress_file(timestamp)
                if progress_file.exists():
                    progress_file.unlink()

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
            st.rerun()

    # Check for navigation button clicks (these are set by on_click callbacks)
    if st.session_state.get('nav_next', False):
        st.session_state.nav_next = False
        if st.session_state.current_slide_idx < len(slides) - 1:
            st.session_state.current_slide_idx += 1
            st.session_state.audio_finished = False
            # Update selectbox to match new slide
            st.session_state.slide_changed_externally = True
            st.rerun()

    if st.session_state.get('nav_prev', False):
        st.session_state.nav_prev = False
        if st.session_state.current_slide_idx > 0:
            st.session_state.current_slide_idx -= 1
            st.session_state.audio_finished = False
            # Update selectbox to match new slide
            st.session_state.slide_changed_externally = True
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

    # Initialize Q&A panel state
    if 'qa_panel_open' not in st.session_state:
        st.session_state.qa_panel_open = False

    current_slide = slides[current_idx]
    current_narration = narrations[current_idx]

    # === 2. SLIDE SELECTOR BAR ===
    # Create slide options for selectbox (cache to avoid regenerating on every rerender)
    audio_ready_hash = tuple(st.session_state.audio_ready)  # Use tuple for hashability

    if 'cached_slide_options' not in st.session_state or st.session_state.get('cached_audio_hash') != audio_ready_hash:
        slide_options = []
        for idx, slide in enumerate(slides):
            audio_indicator = "🔊" if st.session_state.audio_ready[idx] else "⏳"
            slide_options.append(f"{audio_indicator} Slide {idx + 1}/{len(slides)}: {slide.title}")
        st.session_state.cached_slide_options = slide_options
        st.session_state.cached_audio_hash = audio_ready_hash
    else:
        slide_options = st.session_state.cached_slide_options

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

    # === CREATE CENTERED LAYOUT FOR PRESENTATION ===
    # Use columns to center the toolbar, slide selector, slide, and controls
    # Always use same layout - Q&A panel will be handled within slide area
    _left_pad, presentation_col, _right_pad = st.columns([1, 6, 1])

    # Toolbar and slide selector inside the centered column
    with presentation_col:
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
            # Export button - generates PDF with slides and narrations
            st.download_button(
                label="📥",
                data=lambda : generate_narration_pdf(slides, narrations),
                file_name=f"narrations_{st.session_state.get('timestamp', 'export')}.pdf",
                mime="application/pdf",
                help="Download Narrations as PDF",
                width="stretch"
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


        # Slide selector
        st.selectbox(
            label="Navigate to slide:",
            options=slide_options,
            key="slide_selector_value",
            on_change=on_slide_select,
            label_visibility="collapsed"
        )

        # === 3. SLIDE DISPLAY WITH Q&A PANEL ===
        # When Q&A is open, create columns within this area only
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
                # Show original high-res image
                st.image(
                    BytesIO(current_slide.image_data),
                    width="stretch"
                )

                # Preload adjacent slides into cache for instant navigation
                if current_idx > 0 and slides[current_idx - 1].image_data:
                    pass  # No need to cache, always show original
                if current_idx < len(slides) - 1 and slides[current_idx + 1].image_data:
                    pass
            else:
                st.markdown(current_slide.content)

            # Speaker notes (if available)
            if current_slide.notes:
                with st.expander("📝 Speaker Notes"):
                    st.markdown(current_slide.notes)

        # === Q&A PANEL (if open) ===
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
                                    
                                    function checkAnswerFinished() {
                                        const finished = localStorage.getItem('answer_audio_finished');
                                        if (finished === 'true') {
                                            localStorage.removeItem('answer_audio_finished');
                                            const buttons = window.parent.document.querySelectorAll('button');
                                            for (let btn of buttons) {
                                                if (btn.textContent.includes('answer_done_hidden')) {
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
                                    additional_context=None,
                                    use_vision=True  # Enable vision to include slide image in context
                                )

                                st.session_state.current_answer = answer

                                if not st.session_state.get('test_mode', True):
                                    try:
                                        tts = TTSEngine(
                                            voice=st.session_state.get('tts_voice', Config.TTS_VOICE)
                                        )  # Uses Config.TTS_PROVIDER

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
        # Controls bar (continue in presentation_col)
        st.markdown("---")

        control_col1, control_col2, control_col3 = st.columns([1, 8, 1])

        with control_col1:
            # Previous button (only active if not first slide)
            if current_idx > 0:
                st.button(
                    "⬅️",
                    key="prev_slide",
                    width="stretch",
                    on_click=lambda: st.session_state.update({'nav_prev': True})
                )
            else:
                st.button("⬅️", key="prev_slide_disabled", disabled=True, width="stretch")

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
                        "➡️",
                        key="next_slide",
                        width="stretch",
                        on_click=lambda: st.session_state.update({'nav_next': True})
                    )
                else:
                    st.button("➡️", key="next_slide_waiting", disabled=True, width="stretch", help="⏳ Audio generating...")
            else:
                st.button("➡️", key="next_slide_disabled", disabled=True, width="stretch")

        # === 5. NARRATION EXPANDER ===
        # Place at presentation_col level to span full width
        with st.expander("📄 Narration", expanded=False):
            st.markdown(current_narration.narration_text)

    # Auto-advance polling (outside the presentation_col, as it's hidden)
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


def generate_narration_pdf(slides, narrations) -> bytes:
    """
    Generate a PDF export of presentation with slide images and narrations.
    
    Args:
        slides: List of Slide objects containing image data
        narrations: List of SlideNarration objects
        
    Returns:
        PDF file as bytes
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, 
                           topMargin=0.75*inch, bottomMargin=0.75*inch,
                           leftMargin=0.75*inch, rightMargin=0.75*inch)
    
    # Container for PDF elements
    story = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor='#2c3e50',
        spaceAfter=30,
        alignment=TA_CENTER
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor='#34495e',
        spaceAfter=12,
        spaceBefore=12
    )
    stat_style = ParagraphStyle(
        'StatStyle',
        parent=styles['Normal'],
        fontSize=12,
        textColor='#555555',
        spaceAfter=8,
        alignment=TA_LEFT
    )
    narration_style = ParagraphStyle(
        'NarrationStyle',
        parent=styles['Normal'],
        fontSize=11,
        textColor='#333333',
        spaceAfter=6,
        alignment=TA_LEFT,
        leading=14
    )
    duration_style = ParagraphStyle(
        'DurationStyle',
        parent=styles['Italic'],
        fontSize=10,
        textColor='#7f8c8d',
        spaceAfter=20,
        alignment=TA_LEFT
    )
    
    # Calculate statistics
    total_slides = len(narrations)
    total_duration = sum(n.estimated_duration for n in narrations)
    total_minutes = int(total_duration // 60)
    total_seconds = int(total_duration % 60)
    
    # Add title page with statistics
    story.append(Paragraph("PRESENTATION NARRATIONS", title_style))
    story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph("<b>Presentation Statistics</b>", heading_style))
    story.append(Paragraph(f"<b>Total Slides:</b> {total_slides}", stat_style))
    story.append(Paragraph(f"<b>Estimated Presentation Time:</b> {total_minutes} minutes {total_seconds} seconds", stat_style))
    story.append(Paragraph(f"<b>Average Time per Slide:</b> {total_duration/total_slides:.1f} seconds", stat_style))
    
    story.append(Spacer(1, 0.5*inch))
    story.append(PageBreak())
    
    # Add each slide with its narration
    for i, narration in enumerate(narrations):
        # Find corresponding slide
        slide = slides[i] if i < len(slides) else None
        
        # Add slide number as heading
        story.append(Paragraph(f"Slide {narration.slide_number}", heading_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Add slide image if available
        if slide and slide.image_data:
            try:
                # Load image from bytes
                img = PILImage.open(BytesIO(slide.image_data))
                
                # Calculate scaled dimensions to fit width (max 6 inches wide)
                max_width = 6.5 * inch
                max_height = 4.5 * inch
                
                img_width, img_height = img.size
                aspect_ratio = img_height / img_width
                
                # Scale to fit within max dimensions
                if img_width > max_width:
                    new_width = max_width
                    new_height = new_width * aspect_ratio
                else:
                    new_width = img_width
                    new_height = img_height
                
                # Check if height exceeds max
                if new_height > max_height:
                    new_height = max_height
                    new_width = new_height / aspect_ratio
                
                # Save to temporary buffer
                img_buffer = BytesIO()
                img.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                
                # Add image to PDF
                rl_img = RLImage(img_buffer, width=new_width, height=new_height)
                story.append(rl_img)
                story.append(Spacer(1, 0.2*inch))
            except Exception as e:
                # If image fails to load, just continue
                story.append(Paragraph(f"<i>[Image unavailable]</i>", narration_style))
                story.append(Spacer(1, 0.2*inch))
        
        # Add narration text
        story.append(Paragraph("<b>Narration:</b>", narration_style))
        # Break narration into paragraphs if it contains newlines
        narration_paragraphs = narration.narration_text.split('\n')
        for para in narration_paragraphs:
            if para.strip():
                story.append(Paragraph(para, narration_style))
        
        story.append(Spacer(1, 0.1*inch))
        
        # Add duration
        duration_text = f"Estimated duration: {narration.estimated_duration:.1f} seconds ({narration.estimated_duration/60:.1f} minutes)"
        story.append(Paragraph(duration_text, duration_style))
        
        # Add page break after each slide (except the last one)
        if i < len(narrations) - 1:
            story.append(PageBreak())
    
    # Build PDF
    doc.build(story)
    
    # Get PDF bytes
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes


if __name__ == "__main__":
    main()

