import os

from maia.voice.classes.whisper_stt import WhisperSTT
from maia.voice.classes.mock_stt import MockSTT

# Load models conditionally to save memory on local development
use_mock = os.getenv("MAIA_MOCK_STT_AND_TTS", "0") == "1"

if use_mock:
    stt_engine = MockSTT()
else:
    stt_engine = WhisperSTT()


def transcribe_audio(audio_path: str) -> str:
    return stt_engine.transcribe_audio(audio_path)
