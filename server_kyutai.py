# path to cache hub file to avoir redownloading
# os.environ["HF_HUB_CACHE"] = r"C:\path\to\copied\hub"   # or wherever you put it
# os.environ["HF_HUB_OFFLINE"] = "1"

import threading

from pathlib import Path
from fastapi import FastAPI
from pydantic import BaseModel

import numpy as np
import soundfile as sf
import torch
import torch._dynamo

torch._dynamo.config.disable = True  # need to do that before import moshi
from moshi.models.loaders import CheckpointInfo  # noqa: E402
from moshi.models.tts import TTSModel  # noqa: E402

# Make sure to make one generation at a time
model_lock = threading.Lock()

app = FastAPI()

SAMPLE_RATE = 24000
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Loading Kyutai TTS on {DEVICE}...")
checkpoint_info = CheckpointInfo.from_hf_repo("kyutai/tts-1.6b-en_fr")
model = TTSModel.from_checkpoint_info(checkpoint_info, device=torch.device(DEVICE))
print("Model loaded.")

# Map your integer voice IDs to Kyutai voice refs (repo names)
VOICE_MAP = {
    0: "unmute-prod-website/developpeuse-3.wav",  # Estelle
    1: "cml-tts/fr/10177_10625_000134-0003_enhanced.wav",  # Corinne
    2: "cml-tts/fr/12080_11650_000047-0001.wav",  # Nicole
    3: "cml-tts/fr/12205_11650_000004-0002_enhanced.wav",  # Natasha
    4: "cml-tts/fr/1591_1028_000108-0004_enhanced.wav",  # Chantal
    5: "cml-tts/fr/5207_3078_000031-0002_enhanced.wav",  # Pauline
    6: "cml-tts/fr/5476_3103_000072-0001_enhanced.wav",  # Clara
    7: "cml-tts/fr/577_394_000070-0001_enhanced.wav",  # Diana
    8: "unmute-prod-website/degaulle-2.wav",
    9: "cml-tts/fr/2114_1656_000053-0001_enhanced.wav",  # Quebecois
}

# Preload voices
print("Preload voices...")

VOICE_COND = {}
CFG_COEF = 2.0
for i in VOICE_MAP:
    voice_path = model.get_voice_path(VOICE_MAP[i])
    cond = model.make_condition_attributes([voice_path], cfg_coef=CFG_COEF)
    VOICE_COND[i] = cond

print("Voices loaded.")


class GenerateRequest(BaseModel):
    text: str
    voice: int
    output_path: str  # relative path where the server should write the wav


@app.post("/generate")
def generate(req: GenerateRequest):
    entries = model.prepare_script([req.text], padding_between=1)
    condition_attributes = VOICE_COND.get(req.voice, VOICE_COND[0])

    pcms = []

    def _on_frame(frame):
        if (frame[:, 1:] != -1).all():
            pcm = model.mimi.decode(frame[:, 1:, :]).cpu().numpy()
            pcms.append(np.clip(pcm[0, 0], -1, 1))

    with model_lock:
        with model.mimi.streaming(1):
            model.generate([entries], [condition_attributes], on_frame=_on_frame)

    audio = np.concatenate(pcms, axis=-1)
    Path(req.output_path).parent.mkdir(parents=True, exist_ok=True)
    sf.write(req.output_path, audio.T, samplerate=SAMPLE_RATE)
    return {"status": "ok", "output_path": req.output_path}


@app.get("/health")
def health():
    return {"status": "ok", "device": DEVICE}
