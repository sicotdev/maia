class MockSTT:
    """
    Mock TTS engine for local development where actual models are not loaded.
    It simulates audio generation by creating a dummy file or yielding dummy data.
    """

    def __init__(self):
        print("[MockSTT] Initialized")

    def transcribe_audio(self, audio_path: str) -> str:
        print("[MockSTT] Generated dummy transcribe")
        return "This is a text"
