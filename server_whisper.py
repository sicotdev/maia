import re
from fastapi import HTTPException
from faster_whisper import WhisperModel

from fastapi import FastAPI
from pydantic import BaseModel

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
    r"^okay,?\s*bye\.?$",
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
    # Match seulement si le segment ENTIER correspond au pattern connu,
    # pas juste une sous-partie — évite de bloquer un usage légitime
    return any(
        re.fullmatch(pattern + r"\.?", normalized) for pattern in HALLUCINATION_PATTERNS
    )


class TranscribeRequest(BaseModel):
    audio_path: str
    user_language: str = "fr"


app = FastAPI()


# Load model globally to avoid reloading on every request
# Use "base" for speed, "small" or "medium" for better accuracy
# Device can be "cuda" (if GPU is available) or "cpu"
MODEL_SIZE = "small"
DEVICE = "cuda"  # Change to "cuda" if GPU is available
COMPUTE_TYPE = "int8"  # Use int8 for to save memory and speed up

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
        segments, info = model.transcribe(
            req.audio_path,
            language=req.user_language,
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
            no_speech_threshold=0.6,
            vad_filter=True,  # faster-whisper a un VAD intégré (Silero), active-le !
            vad_parameters=dict(min_silence_duration_ms=500),
            beam_size=5,
        )

        full_text = ""
        for seg in segments:
            if seg.no_speech_prob > 0.6 or seg.avg_logprob < -1.0:
                continue
            if is_known_hallucination(seg.text):
                continue
            full_text += seg.text + " "

        # print(f"{full_text}")
        return {"text": full_text.strip()}

    except Exception as e:
        print(f"Transcription error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error during transcription: {str(e)}"
        )
