from fastapi import HTTPException
from faster_whisper import WhisperModel

from fastapi import FastAPI
from pydantic import BaseModel


class TranscribeRequest(BaseModel):
    audio_path: str


app = FastAPI()


# Load model globally to avoid reloading on every request
# Use "base" for speed, "small" or "medium" for better accuracy
# Device can be "cuda" (if GPU is available) or "cpu"
MODEL_SIZE = "small"
DEVICE = "cuda"  # Change to "cuda" if GPU is available
COMPUTE_TYPE = "int8"  # Use int8 for CPU to save memory and speed up

print(f"Loading Whisper model ({MODEL_SIZE}) on {DEVICE}...")
try:
    model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
    print("Model loaded successfully.")
except Exception as e:
    print(f"Error loading Whisper model: {e}")
    model = None


@app.post("/transcribe")
def generate(req: TranscribeRequest):
    if model is None:
        raise HTTPException(status_code=500, detail="Whisper model is not loaded.")

    try:
        # Transcribe the audio file
        segments, info = model.transcribe(req.audio_path, beam_size=5)

        full_text = ""
        for segment in segments:
            full_text += segment.text + " "

        print(f"{full_text}")
        return {"text": full_text.strip()}

    except Exception as e:
        print(f"Transcription error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error during transcription: {str(e)}"
        )
