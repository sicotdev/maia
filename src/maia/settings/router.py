from fastapi import APIRouter
from typing import List, Dict


router = APIRouter()

# Données fictives - À remplacer par des requêtes DB ou appels Gateway réels
ENGINES = [
    {"id": "pocket_tts", "name": "Kyutai Pocket TTS"},
    {"id": "kokoro_tts", "name": "Kokoro TTS"},
    {"id": "coqui_x_tts", "name": "Coqui X-TTS"},
    {"id": "cosyvoice_tts", "name": "CosyVoice"},
]

VOICES = [
    {"id": "estelle", "name": "Estelle"},
    {"id": "miel", "name": "Miel"},
    {"id": "isedith", "name": "Isedith"},
]

PROFILES = [
    {"id": "default", "name": "Default", "port": 8642},
    {"id": "assistant", "name": "Assistant", "port": 8646},
    {"id": "friend", "name": "Friend", "port": 8647},
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
