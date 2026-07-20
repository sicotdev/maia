from maia.voice.classes.tts_engine import TTSEngine
import asyncio

class MockTTS(TTSEngine):
    """
    Mock TTS engine for local development where actual models are not loaded.
    It simulates audio generation by creating a dummy file or yielding dummy data.
    """
    def __init__(self):
        print(f"[MockTTS] Initialized")

    def generate_audio(self, text: str, output_file: str, voice: int):
        # Simulate a simple "audio" file creation
        with open(output_file, "w") as f:
            f.write(f"MOCK_AUDIO_DATA: {text}")
        print(f"[MockTTS] Generated dummy audio to {output_file}")

    async def generate_audio_stream(self, text: str, output_name: str, output_dir: str, tmp_dir: str, voice: int):
        # Simulate a stream of chunks
        # In a real scenario, we'd yield bytes. Here we yield a placeholder.
        yield f"event: done\ndata: {output_dir}/{output_name}.wav\n\n"
        print(f"[MockTTS] Yielded dummy stream for {output_name}")
