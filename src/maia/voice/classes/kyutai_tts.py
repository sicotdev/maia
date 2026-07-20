import asyncio

import httpx2
import numpy as np
import soundfile as sf
import requests
       
from maia.voice.classes.tts_engine import TTSEngine

class KyutaiTTS(TTSEngine):
    def __init__(self, base_url: str = "http://127.0.0.1:8756"):
        self.base_url = base_url

    def generate_audio(self, text: str, output_file: str, voice: int):

        resp = requests.post(
            f"{self.base_url}/generate",
            json={"text": text, "voice": voice, "output_path": output_file},
        )
        resp.raise_for_status()


    async def generate_audio_stream(self, text: str, output_name: str, output_dir: str, tmp_dir: str, voice: int):

        chunks = [chunk.strip() for chunk in text.split('\n') if chunk.strip()]
        audio_segments = []

        async with httpx2.AsyncClient(timeout=None) as client:
            for i, chunk in enumerate(chunks):
                chunk_file = f"{tmp_dir}/{output_name}_{i}.wav"

                try:
                    response = await client.post(
                        f"{self.base_url}/generate",
                        json={"text": chunk, "voice": voice, "output_path": chunk_file},
                    )
                    response.raise_for_status()

                    data, samplerate = await asyncio.to_thread(self._process_chunk, chunk_file)

                    yield f"event: chunk\ndata: {chunk_file}\n\n"

                    audio_segments.append(data)

                except Exception as e:
                    print(f"something went wrong on chunk {i}: {e}")
                    yield f"event: error\ndata: chunk {i} failed\n\n"

        #Merge final file
        final_file = f"{output_dir}/{output_name}.wav"
        if (len(audio_segments) > 0):
            merged = np.concatenate(audio_segments, axis=0)
            await asyncio.to_thread(
                self._write_wav, final_file, merged, samplerate=samplerate
            )
        
        yield f"event: done\ndata: {final_file}\n\n"

    @staticmethod
    def _process_chunk(chunk_file: str):
        TTSEngine.normalize_audio(chunk_file, chunk_file)
        data, samplerate = sf.read(chunk_file)
        return data, samplerate

    @staticmethod
    def _write_wav(file: str, audio: np.ndarray, samplerate: int):
        sf.write(file, audio, samplerate)
        TTSEngine.normalize_audio(file, file)
        