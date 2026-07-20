from abc import ABC, abstractmethod
from typing import AsyncIterator

import torch
import soundfile as sf
import numpy as np
import pyloudnorm as pyln

from maia.voice.detect_tts_noise import is_noise_garbage


class TTSEngine(ABC):
    @abstractmethod
    def generate_audio(self, text: str, output_file: str, voice: int):
        """Generate complete audio and write it in output_file."""
        pass

    @abstractmethod
    async def generate_audio_stream(
        self, text: str, output_name: str, output_dir: str, tmp_dir: str, voice: int
    ) -> AsyncIterator[str]:
        """Yield audio chunks as they're generated in tmp_dir, and merge them at the end in output_dir/output_name."""
        if False:
            yield ""  # for pyright

    @staticmethod
    def normalize_audio(
        input_path: str,
        output_path: str,
        target_lufs: float = -19.0,
        peak_limit: float = -1.0,
        max_gain_db: float = 20.0,
    ) -> bool:
        data, rate = sf.read(input_path)
        meter = pyln.Meter(rate)

        min_duration_s = meter.block_size  # 0.4s by default
        duration_s = len(data) / rate
        if duration_s < min_duration_s:
            print("normalize_audio: Input is too short; skipping normalization")
            return False

        loudness = meter.integrated_loudness(data)

        if not np.isfinite(loudness):
            print("normalize_audio: Input is silent or invalid; skipping normalization")
            return False

        gain_db = target_lufs - loudness
        if gain_db > max_gain_db:
            print(
                f"normalize_audio: Gain {gain_db:.1f} dB exceeds max_gain_db; likely broken input"
            )
            return False

        normalized = pyln.normalize.loudness(data, loudness, target_lufs)

        peak = np.max(np.abs(normalized))
        peak_limit_linear = 10 ** (peak_limit / 20)
        if peak > peak_limit_linear:
            normalized = normalized * (peak_limit_linear / peak)

        sf.write(output_path, normalized, rate)
        return True

    @staticmethod
    def is_epic_fail(audio: torch.Tensor):

        # start = time.perf_counter()
        result = is_noise_garbage(
            audio, 24000
        )  # wav_tensor: (samples,) or (channels, samples), float in [-1, 1]
        # elapsed = (time.perf_counter() - start) * 1000
        # print(f"{result} took {elapsed:.2f} ms")

        return result["is_garbage"]
