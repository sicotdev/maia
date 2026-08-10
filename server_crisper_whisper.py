import re
import torch
from fastapi import HTTPException
from pydantic import BaseModel
from fastapi import FastAPI
from crisperwhisper import CrisperWhisper

# Hallucination patterns from the original server_whisper.py
HALLUCINATION_PATTERNS = [
    # Français
    r"sous-titres? réalisés? par",
    r"amara\.org",
    r"merci d'avoir regardé",
    r"abonnez-vous",
    # Anglais - sous-titrage/outro générique
    r"thanks? for watching",
    r"thank you for watching",
    r"please subscribe",
    r"don'?t forget to subscribe",
    r"like and subscribe",
    r"see you (in the )?next (video|time)",
    r"subtitles? (by|provided by|created by)",
    r"captions? (by|provided by)",
    r"transcribed by",
    r"translated by",
    # Anglais - phrases "filler" classiques
    r"i'?ll see you (guys )?next time",
    r"thanks? for listening",
    r"bye[\s\-]?bye",
    r"^okay,\s*bye\.?$",
    # URLs/plateformes récurrentes (résidus de données d'entraînement)
    r"www\.\w+\.(com|org|gr|net)",
    r"youtube\.com",
    # Génériques (silence pur mal interprété)
    r"^\s*\.\s*$",
    r"^\s*silence\s*$",
    r"^\s*\[.*?\]\s*$",  # ex: "[Music]", "[Applause]"
]

def is_known_hallucination(text: str) -> bool:
    normalized = text.strip().lower()
    if not normalized:
        return True
    return any(
        re.fullmatch(pattern + r"\.?", normalized) for pattern in HALLUCINATION_PATTERNS
    )

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
    model = CrisperWhisper(device=DEVICE)
    print("CrisperWhisper model loaded successfully.")
except Exception as e:
    print(f"Error loading CrisperWhisper model: {e}")
    model = None

@app.post("/transcribe")
def generate(req: TranscribeRequest):
    if model is None:
        raise HTTPException(status_code=500, detail="CrisperWhisper model is not loaded.")

    try:
        # CrisperWhisper transcription
        # It returns a list of segments with timestamps
        segments = model.transcribe(
            req.audio_path,
            language=req.user_language,
            # CrisperWhisper handles many of the parameters 
            # internaly for high-quality verbatim.
        )

        full_text = ""
        for seg in segments:
            # Filter based on probabilities (similar to faster-whisper logic)
            # CrisperWhisper segments usually have a confidence/probability score
            if hasattr(seg, 'confidence') and seg.confidence < 0.5:
                continue
            
            if is_known_hallucination(seg.text):
                continue
                
            full_text += seg.text + " "

        return {"text": full_text.strip()}

    except Exception as e:
        print(f"Transcription error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error during transcription: {str(e)}"
        )
