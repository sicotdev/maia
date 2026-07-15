import asyncio
import torch
import torchaudio
import os.path
from pathlib import Path

from cosyvoice.utils.file_utils import load_wav

# Directory the current .py file lives in
BASE_DIR = Path(__file__).resolve().parent
model_wav_path = BASE_DIR / "pocket-models" / "miel-16k.wav"

#CozyVoice 1 or 2
#from cosyvoice.cli.cosyvoice import CosyVoice  # or CosyVoice2, per your model
#cosyvoice = CosyVoice('pretrained_models/CosyVoice-300M')
#prompt_speech_16k = load_wav(model_wav_path, 16000)

#CozyVoice 3
from cosyvoice.cli.cosyvoice import AutoModel
cosyvoice = AutoModel(model_dir='pretrained_models/Fun-CosyVoice3-0.5B', fp16=False)


async def generate_audio(text: str, output_file: str):
    generator = cosyvoice.inference_zero_shot(
        text,
        'You are a helpful assistant and you speak french fluently.<|endofprompt|>Il y en a des lumières là sur ton bureau. Han... Oh les reliques! Regardez, regardez un peu ça là.',  # prompt text matching the reference audio
        #CozyVoice 3
        str(model_wav_path),
        #CozyVoice 1 or 2
        #prompt_speech_16k,
        stream=True,
        text_frontend=False, 
    )

    audios = []
    i = 0

    while True:
        item = await asyncio.to_thread(next, generator, None)
        if item is None:
            break

        audio = item['tts_speech']  # torch tensor, shape (1, N)
        print(i, "generated chunk", audio.shape)

        chunk_file = f"{output_file}_{i}.wav"
        await asyncio.to_thread(torchaudio.save, chunk_file, audio, cosyvoice.sample_rate)

        audios.append(audio)
        yield f"event: chunk\ndata: {chunk_file}\n\n"
        i += 1

    # Concatenate all audio (torch tensors here, along the time dimension)
    full_audio = torch.cat(audios, dim=1)
    final_file = f"{output_file}.wav"
    await asyncio.to_thread(torchaudio.save, final_file, full_audio, cosyvoice.sample_rate)

    yield f"event: done\ndata: {final_file}\n\n"