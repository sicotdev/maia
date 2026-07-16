import os
import torch
from fastapi import HTTPException
from faster_whisper import WhisperModel
from maia.logging_config import logger


# Load model globally to avoid reloading on every request
# Use "base" for speed, "small" or "medium" for better accuracy
# Device can be "cuda" (if GPU is available) or "cpu"
MODEL_SIZE = "small"
DEVICE = "cpu" # Change to "cuda" if GPU is available
COMPUTE_TYPE = "int8" # Use int8 for CPU to save memory and speed up

logger.info(f"Loading Whisper model ({MODEL_SIZE}) on {DEVICE}...")
try:
    model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
    logger.info("Model loaded successfully.")
except Exception as e:
    logger.error(f"Error loading Whisper model: {e}")
    model = None

def transcribe_audio(audio_path: str) -> str:
    if model is None:
        raise HTTPException(status_code=500, detail="Whisper model is not loaded.")
    
    try:
        # Transcribe the audio file
        segments, info = model.transcribe(audio_path, beam_size=5)
        
        full_text = ""
        for segment in segments:
            full_text += segment.text + " "
        
        return full_text.strip()
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Error during transcription: {str(e)}")
