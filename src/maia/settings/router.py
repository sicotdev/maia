from fastapi import APIRouter
from typing import List, Dict


router = APIRouter()

# Données fictives - À remplacer par des requêtes DB ou appels Gateway réels
ENGINES = [
    {"id": "google", "name": "Google Cloud TTS"},
    {"id": "amazon", "name": "Amazon Polly"},
    {"id": "microsoft", "name": "Microsoft Azure TTS"},
    {"id": "elevenlabs", "name": "ElevenLabs"},
]

VOICES = [
    {"id": "voice_1", "name": "Google Française (Feminine)"},
    {"id": "voice_2", "name": "Google Française (Masculine)"},
    {"id": "voice_3", "name": "Microsoft Valérie"},
    {"id": "voice_4", "name": "Amazon Polly - French (Joanna)"},
]

PROFILES = [
    {"id": "default", "name": "Default", "port": 8645},
    {"id": "work", "name": "Work", "port": 8646},
    {"id": "creative", "name": "Creative", "port": 8647},
]

@router.get("")
async def get_settings_data():
    """
    Retourne la liste des moteurs, des voix et des profils en une seule requête.
    """
    return {
        "engines": ENGINES,
        "voices": VOICES,
        "profiles": PROFILES
    }
