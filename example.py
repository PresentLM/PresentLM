"""
Example script demonstrating PresentLM workflow.
This shows how to use all the components together.
"""

from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core import (
    SlideParser,
    NarrationGenerator,
    TTSEngine,
    QuestionHandler,
)
from src.utils import Config, save_json


def main():
    """Run example PresentLM workflow."""
    
    print("🎤 PresentLM Example Workflow\n")
    
    # Validate configuration
    print("1️⃣ Validating configuration...")
    try:
        Config.validate()
        print("✅ Configuration valid\n")
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("Please set up your .env file with API keys")
        return
    
    # Example slide deck path (you need to provide your own)
    slide_path = Config.SLIDES_DIR / "example_presentation.pdf"
    
    if not slide_path.exists():
        print(f"❌ Example slide deck not found at: {slide_path}")
        print("\nTo run this example:")
        print("1. Place a PDF slide deck at: data/slides/example_presentation.pdf")
        print("2. Or modify the slide_path variable in this script")
        return
    
    # Step 1: Parse slides
    print("2️⃣ Parsing slides...")
    parser = SlideParser(use_vision=False)
    slides = parser.parse(slide_path)
    print(f"✅ Parsed {len(slides)} slides\n")
    
    for i, slide in enumerate(slides[:3], 1):  # Show first 3
        print(f"   Slide {i}: {slide.title}")
    print()
    
    # Step 2: Generate narrations
    print("3️⃣ Generating narrations...")
    narration_gen = NarrationGenerator()
    
    # Optional context
    context = """
    This is a lecture on machine learning fundamentals.
    The audience is university students with basic programming knowledge.
    """
    
    narrations = narration_gen.generate_narration(
        slides,
        context=context,
        style="educational"
    )
    print(f"✅ Generated {len(narrations)} narrations\n")
    
    # Show first narration
    print(f"   Example narration for slide 1:")
    print(f"   {narrations[0].narration_text[:200]}...\n")
    
    # Step 3: Generate audio
    print("4️⃣ Generating audio (first 3 slides)...")
    tts = TTSEngine()
    
    audio_segments = []
    for i, narration in enumerate(narrations[:3]):  # Just first 3 for demo
        print(f"   Generating audio for slide {narration.slide_number}...")
        audio_path = Config.AUDIO_DIR / f"example_slide_{narration.slide_number}.mp3"
        
        segment = tts.generate_audio(
            narration.narration_text,
            audio_path,
            speed=1.0
        )
        segment.slide_number = narration.slide_number
        audio_segments.append(segment)
        
        print(f"   ✅ Saved to: {audio_path}")
    
    print()
    
    # Step 4: Question answering demo
    print("5️⃣ Question answering demo...")
    question_handler = QuestionHandler()
    
    # Example question
    question = "Can you explain what propositional logic is?"
    print(f"   Q: {question}")
    
    answer = question_handler.answer_question(
        question=question,
        current_slide=slides[0],
        current_narration=narrations[0],
        all_slides=slides,
        additional_context=context,
        use_vision=True  # Enable vision to include slide image in context
    )
    
    print(f"   A: {answer[:200]}...\n")
    
    # Save summary
    print("6️⃣ Saving presentation summary...")
    summary = {
        "num_slides": len(slides),
        "slides": [
            {
                "number": s.slide_number,
                "title": s.title,
                "has_notes": bool(s.notes)
            }
            for s in slides
        ],
        "narrations_generated": len(narrations),
        "audio_files_generated": len(audio_segments),
        "total_estimated_duration": sum(n.estimated_duration for n in narrations)
    }
    
    summary_path = Config.DATA_DIR / "example_summary.json"
    save_json(summary, summary_path)
    print(f"✅ Summary saved to: {summary_path}\n")
    
    print("🎉 Example workflow complete!")
    print("\nNext steps:")
    print("1. Check the generated audio files in: data/audio/")
    print("2. Run the UI: streamlit run src/ui/app.py")
    print("3. Explore the full presentation experience!")


if __name__ == "__main__":
    main()
