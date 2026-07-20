"""
Torch-native noise-garbage detector for TTS output.
Takes a waveform tensor directly -- no file I/O.
"""

import torch


@torch.no_grad()
def is_noise_garbage(
    wav: torch.Tensor,
    sr: int,
    n_fft: int = 2048,
    hop_length: int = 512,
    flatness_threshold: float = 0.35,
    clip_threshold: float = 0.98,
    clip_ratio_threshold: float = 0.01,
    rms_dbfs_threshold: float = -6.0,
) -> dict:
    """
    wav: 1D tensor (mono) or 2D tensor (channels, samples). Values assumed
         in [-1, 1] float range (typical TTS output convention).
    sr:  sample rate, only used to report duration -- not needed for the
         math itself.

    Returns a dict of features + `is_garbage` bool. Same logic/thresholds
    as the librosa version: high spectral flatness + high loudness/clipping.
    """
    if wav.dim() == 2:
        wav = wav.mean(dim=0)  # downmix to mono
    wav = wav.float()

    # --- Spectral flatness (Wiener entropy) ---
    window = torch.hann_window(n_fft, device=wav.device)
    stft = torch.stft(
        wav, n_fft=n_fft, hop_length=hop_length, window=window,
        return_complex=True, center=True,
    )
    mag = stft.abs().clamp_min(1e-10)  # (freq, frames)

    log_mag = torch.log(mag)
    geo_mean = torch.exp(log_mag.mean(dim=0))   # per-frame geometric mean
    arith_mean = mag.mean(dim=0)                # per-frame arithmetic mean
    flatness_per_frame = geo_mean / arith_mean
    flatness = flatness_per_frame.mean().item()

    # --- Loudness / clipping ---
    rms = wav.pow(2).mean().sqrt().clamp_min(1e-12)
    rms_dbfs = (20 * torch.log10(rms)).item()
    clip_ratio = (wav.abs() >= clip_threshold).float().mean().item()

    flat_flag = flatness > flatness_threshold
    loud_flag = (rms_dbfs > rms_dbfs_threshold) or (clip_ratio > clip_ratio_threshold)
    garbage = flat_flag and loud_flag

    return {
        "spectral_flatness": flatness,
        "clip_ratio": clip_ratio,
        "rms_dbfs": rms_dbfs,
        "flat_flag": flat_flag,
        "loud_flag": loud_flag,
        "is_garbage": garbage,
        "duration_s": wav.shape[-1] / sr,
    }


def clean_or_silence(wav: torch.Tensor, sr: int, **kwargs) -> torch.Tensor:
    """
    Returns either the original tensor, or a zero tensor of the same
    shape/dtype/device if classified as garbage. Also returns the
    diagnostic dict for logging.
    """
    result = is_noise_garbage(wav, sr, **kwargs)
    if result["is_garbage"]:
        return torch.zeros_like(wav), result
    return wav, result


if __name__ == "__main__":
    import time

    sr = 22050
    dur_s = 3
    n = sr * dur_s

    noise = (torch.rand(n) * 2 - 1) * 0.95
    t = torch.linspace(0, dur_s, n)
    tone = 0.2 * torch.sin(2 * 3.14159 * 220 * t) + 0.1 * torch.sin(2 * 3.14159 * 440 * t)

    for name, w in [("noise", noise), ("tone", tone)]:
        start = time.perf_counter()
        res = is_noise_garbage(w, sr)
        elapsed = (time.perf_counter() - start) * 1000
        print(f"{name}: {res} | took {elapsed:.2f} ms")
