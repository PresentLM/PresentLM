"""
Test script to verify TTS provider configuration.
Run this to test OpenAI or Qwen TTS setup.
"""

from src.core.tts_engine import TTSEngine
from src.utils.config import Config

def test_tts_provider():
    """Test the configured TTS provider."""
    print("=" * 60)
    print("TTS Provider Test")
    print("=" * 60)

    # Show current configuration
    print(f"\n📋 Current Configuration:")
    print(f"   TTS Provider: {Config.TTS_PROVIDER}")
    print(f"   TTS Voice: {Config.TTS_VOICE}")
    print(f"   TTS Speed: {Config.TTS_SPEED}")

    # Validate configuration
    try:
        Config.validate()
        print(f"   ✅ Configuration is valid\n")
    except ValueError as e:
        print(f"   ❌ Configuration error: {e}")
        return

    # Initialize TTS engine
    print(f"🔧 Initializing TTS Engine...")
    try:
        tts = TTSEngine()
        print(f"   ✅ TTS Engine initialized")
        print(f"   Provider: {tts.provider}")
        print(f"   Voice: {tts.voice}\n")
    except Exception as e:
        print(f"   ❌ Failed to initialize: {e}")
        return

    # Generate test audio
    test_text = "Hello! This is a test of the text to speech system. If you can hear this, the TTS provider is working correctly."
    output_path = Config.AUDIO_DIR / "test_tts.mp3"

    print(f"🎤 Generating test audio...")
    print(f"   Text: '{test_text[:50]}...'")
    print(f"   Output: {output_path}")

    try:
        segment = tts.generate_audio(test_text, output_path, speed=1.0)
        print(f"   ✅ Audio generated successfully!")
        print(f"   Duration: {segment.duration:.2f} seconds")
        print(f"   Path: {segment.audio_path}")
        print(f"\n✨ Test completed successfully!")
        print(f"   Play the audio at: {output_path}")
    except Exception as e:
        print(f"   ❌ Audio generation failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)

def compare_providers():
    """Compare OpenAI and Qwen TTS (if both are configured)."""
    print("=" * 60)
    print("TTS Provider Comparison")
    print("=" * 60)

    test_text = "This is a comparison test of text to speech providers."

    providers = []

    # Check OpenAI
    if Config.OPENAI_API_KEY:
        providers.append(("openai", "alloy"))

    # Qwen is always available (runs locally)
    providers.append(("qwen", "en-Female1"))

    if not providers:
        print("❌ No TTS providers configured")
        return

    print(f"\n📋 Testing {len(providers)} provider(s)\n")

    for provider, voice in providers:
        print(f"🎤 Testing {provider.upper()} TTS...")
        try:
            tts = TTSEngine(provider=provider, voice=voice)
            output_path = Config.AUDIO_DIR / f"test_{provider}.mp3"
            segment = tts.generate_audio(test_text, output_path)
            print(f"   ✅ {provider}: Generated {segment.duration:.2f}s audio")
            print(f"      File: {output_path}")
        except Exception as e:
            print(f"   ❌ {provider}: Failed - {e}")
        print()

    print("=" * 60)

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "compare":
        compare_providers()
    else:
        test_tts_provider()
        print("\n[Tip] Run 'python test_tts.py compare' to compare providers")



