import httpx2
import requests


class WhisperSTT:
    def __init__(self, base_url: str = "http://127.0.0.1:8758"):
        self.base_url = base_url

    # TODO: async
    def transcribe_audio(self, audio_path: str) -> str:

        resp = requests.post(
            f"{self.base_url}/transcribe",
            json={"audio_path": audio_path},
        )
        resp.raise_for_status()
        result = resp.json()

        return result["text"]
