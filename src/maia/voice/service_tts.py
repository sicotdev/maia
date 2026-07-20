import emoji
import soundfile as sf
import numpy as np
import re

from maia.voice.classes.tts_engine import TTSEngine
from maia.voice.classes.pocket_tts import PocketTTS
from maia.voice.classes.kokoro_tts import KokoroTTS
from maia.voice.classes.kyutai_tts import KyutaiTTS
from maia.voice.classes.coqui_x_tts import CoquiXTTS
from maia.voice.classes.mock_tts import MockTTS
import os

# Load models conditionally to save memory on local development
use_mock = os.getenv("MAIA_MOCK_TTS", "false").lower() == "true"

if use_mock:
    tts_engines = [MockTTS(), MockTTS(), MockTTS(), MockTTS()]
else:
    tts_engines = [
        PocketTTS(),
        KyutaiTTS(),
        CoquiXTTS(),
        KokoroTTS(),
    ]



def filter_text(text: str) -> str:
    # Remove emojis
    text = emoji.replace_emoji(text, replace="")

    # Replace file names with explicit "point" in french (and other few things)
    ext = {
        ".js": " point JS",
        ".py": " point pi",
        ".md": " point MD",
        ".toml": " point TOML",
        "TODO": "tout doux",
        "README": "readme",
        " & ": " et ",
        " :": ",",
        "backend": "back-end",
        "frontend": "front-end",
        "À": "à",
        "/": ", ",
    }
    for search, replaced in ext.items():
        text = re.sub(re.escape(search), replaced, text, flags=re.IGNORECASE)

    # Replace float numbers (ex: 12.5)
    regex = r"(\d+)\.(\d+)"
    replacement = r"\1 point \2"
    text = re.sub(regex, replacement, text)

    # Test:
    # text = text.replace('Intelligence', "intelligence.")
    return text


def generate_audio(engine: int, text: str, output_file: str, voice: int):
    text = filter_text(text)
    tts_engines[engine].generate_audio(text, output_file, voice)
    TTSEngine.normalize_audio(output_file, output_file)


def merge_audio(chunk_files: list, output_file: str):
    print(f"merging to: {output_file}")

    data_list = []
    samplerate = None
    subtype = None

    for filename in chunk_files:
        data, sr = sf.read(filename)
        if samplerate is None:
            samplerate = sr
            subtype = sf.info(filename).subtype
        elif sr != samplerate:
            raise ValueError(
                f"Sample rate mismatch in {filename}: {sr} != {samplerate}"
            )
        data_list.append(data)

    if len(data_list) == 0 or not samplerate or not subtype:
        return

    merged = np.concatenate(data_list, axis=0)
    sf.write(output_file, merged, samplerate, subtype=subtype)
    TTSEngine.normalize_audio(output_file, output_file)


async def generate_audio_stream(
    engine: int, text: str, output_name: str, output_dir: str, tmp_dir: str, voice: int
):
    text = filter_text(text)
    async for chunk in tts_engines[engine].generate_audio_stream(
        text, output_name, output_dir, tmp_dir, voice
    ):
        yield chunk
