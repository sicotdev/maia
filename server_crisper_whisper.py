import torch
from fastapi import HTTPException
from pydantic import BaseModel
from fastapi import FastAPI
from crisperwhisper import CrisperWhisperModel


class TranscribeRequest(BaseModel):
    audio_path: str
    user_language: str = "fr"


app = FastAPI()

# Load CrisperWhisper model globally
# Using the default model from the repo.
# Device will be "cuda" if available, else "cpu"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Loading CrisperWhisper model on {DEVICE}...")

try:
    # Initializing CrisperWhisper.
    # The library handles model loading via huggingface hub automatically.
    model = CrisperWhisperModel(
        "small",
        backend="transformers",
        device=DEVICE,
    )  # )  # nyralabs/CrisperWhisper2.0_large
    # or pick a size: CrisperWhisperModel("turbo")  # turbo / medium / small

    print("CrisperWhisper model loaded successfully.")
except Exception as e:
    print(f"Error loading CrisperWhisper model: {e}")
    model = None


@app.post("/transcribe")
def generate(req: TranscribeRequest):
    if model is None:
        raise HTTPException(
            status_code=500, detail="CrisperWhisper model is not loaded."
        )

    try:
        # CrisperWhisper transcription
        # It returns a list of segments with timestamps
        clean = model.transcribe(
            req.audio_path,
            language=req.user_language,
            mode="intended",  # Intended: the clean, readable version
        )

        # print(clean)

        return {"text": clean.text.strip()}

    except Exception as e:
        print(f"Transcription error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error during transcription: {str(e)}"
        )
