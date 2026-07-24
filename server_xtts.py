# path to cache hub file to avoir redownloading
# os.environ["HF_HUB_CACHE"] = r"C:\path\to\copied\hub"   # or wherever you put it
# os.environ["HF_HUB_OFFLINE"] = "1"

import torch
import torchaudio
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts, XttsAudioConfig, XttsArgs
from TTS.config.shared_configs import BaseDatasetConfig

from fastapi import FastAPI
from pydantic import BaseModel


VOICES = [
    {"id": "estelle", "name": "Estelle"},
    {"id": "Corinne", "name": "Corinne"},
    {"id": "Nicole", "name": "Nicole"},
    {"id": "Natasha", "name": "Natasha"},
    {"id": "Chantal", "name": "Chantal"},
    {"id": "Pauline", "name": "Pauline"},
    {"id": "Clara", "name": "Clara"},
    {"id": "Diana", "name": "Diana"},
    {"id": "DeGaulle", "name": "De Gaulle"},
    {"id": "Quebecois", "name": "Quebecois"},
    {"id": "miel", "name": "Miel"},
    {"id": "isedith", "name": "Isedith"},
    {"id": "kat", "name": "Katlyn"},
]
VOICE_SAMPLES_DIR = "src/maia/voice/samples"


app = FastAPI()

SAMPLE_RATE = 24000
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Loading XTTS on {DEVICE}...")

# Required due to PyTorch 2.6+ weights_only default change
torch.serialization.add_safe_globals(
    [
        XttsConfig,
        XttsAudioConfig,
        XttsArgs,
        BaseDatasetConfig,
    ]
)

XTTS_MODEL_DIR = "pretrained_models/xtts_v2"
DEVICE = "cuda"  # Change to "cuda" if GPU is available
print(f"Loading xtts_v2 model on {DEVICE}...")

config = XttsConfig()
config.load_json(f"{XTTS_MODEL_DIR}/config.json")
xtts_model = Xtts.init_from_config(config)
xtts_model.load_checkpoint(config, checkpoint_dir=XTTS_MODEL_DIR, use_deepspeed=False)

if DEVICE == "cuda":
    xtts_model.cuda()
print("Model loaded successfully.")

voice_states = []
for voice in VOICES:
    model_wav_path = f"{VOICE_SAMPLES_DIR}/{voice['id']}.wav"
    gpt_cond_latent, speaker_embedding = xtts_model.get_conditioning_latents(
        audio_path=[str(model_wav_path)]
    )
    voice_states.append(
        {
            "gpt_cond_latent": gpt_cond_latent,
            "speaker_embedding": speaker_embedding,
        }
    )


class GenerateRequest(BaseModel):
    text: str
    voice: int
    output_path: str  # relative path where the server should write the wav


@app.post("/generate")
def generate(req: GenerateRequest):

    result = xtts_model.inference(
        req.text,
        "fr",
        voice_states[req.voice]["gpt_cond_latent"],
        voice_states[req.voice]["speaker_embedding"],
        speed=1.0,
        temperature=0.65,
        repetition_penalty=5.0,
        # top_k=50,
        # top_p=0.85,
        # length_penalty=1.0,
        # enable_text_splitting=True,
    )

    audio = torch.tensor(result["wav"]).unsqueeze(
        0
    )  # inference() returns a numpy array under "wav"
    torchaudio.save(req.output_path, audio, 24000)

    return {"status": "ok", "output_path": req.output_path}


@app.get("/health")
def health():
    return {"status": "ok", "device": DEVICE}
