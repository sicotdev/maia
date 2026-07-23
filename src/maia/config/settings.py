# Données fictives - À remplacer par des requêtes DB ou appels Gateway réels
ENGINES = [
    {"id": "pocket_tts", "name": "Kyutai Pocket TTS"},
    {"id": "kyutai_tss", "name": "Kyutai Large TTS"},
    {"id": "coqui_x_tts", "name": "Coqui X-TTS"},
    {"id": "kokoro_tts", "name": "Kokoro TTS"},
]

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

LLM_ENDPOINTS = [
    {"id": "hermes", "name": "Hermes"},
    {"id": "custom", "name": "Custom"},
]

PROFILES = [
    {"id": "default", "name": "Default", "port": 8642},
    {"id": "assistant", "name": "Assistant", "port": 8646},
    {"id": "friend", "name": "Friend", "port": 8647},
]

SETTINGS = {
    "engines": ENGINES,
    "voices": VOICES,
    "profiles": PROFILES,
    "llmEndpoints": LLM_ENDPOINTS,
}
