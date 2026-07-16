import asyncio
import torch
import torchaudio
from pathlib import Path
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
from maia.logging_config import logger

# Required due to PyTorch 2.6+ weights_only default change
torch.serialization.add_safe_globals([XttsConfig])

BASE_DIR = Path(__file__).resolve().parent
model_wav_path = BASE_DIR / "pocket-models" / "isemerge-enhanced-v2.wav"
#model_wav_path = BASE_DIR / "pocket-models" / "miel-enhanced-v2.wav"
#model_wav_path = BASE_DIR / "pocket-models" / "moi2.wav"


# Adjust to the path ModelManager printed in step 2
XTTS_MODEL_DIR = "pretrained_models/xtts_v2"
DEVICE = 'cpu' # Change to "cuda" if GPU is available

logger.info(f"Loading xtts_v2 model on {DEVICE}...")

# Load once at startup
try:
    config = XttsConfig()
    config.load_json(f"{XTTS_MODEL_DIR}/config.json")
    xtts_model = Xtts.init_from_config(config)
    xtts_model.load_checkpoint(config, checkpoint_dir=XTTS_MODEL_DIR, use_deepspeed=False)

    #TODO: install torch with cuda
    if (DEVICE == 'cuda'):
        xtts_model.cuda()
    logger.info("Model loaded successfully.")
except Exception as e:
    logger.error(f"Error loading xtts_v2 model: {e}")
    xtts_model = None

# Compute reference-voice conditioning once at startup too, since it's reusable
gpt_cond_latent, speaker_embedding = xtts_model.get_conditioning_latents(
    audio_path=[str(model_wav_path)]
)


async def generate_audio(text: str, output_file: str):

    if xtts_model is None:
        raise HTTPException(status_code=500, detail="xtts_v2 model is not loaded.")

    # Split ignoring empty chunk
    chunks = [chunk.strip() for chunk in text.split('\n') if chunk.strip()]

    audios = []
    length = len(chunks)
    for i, chunk in enumerate(chunks):
        print(f'GENERATING {i+1}/{length}: {chunk}')

        result = await asyncio.to_thread(
            xtts_model.inference,
            chunk,
            "fr",
            gpt_cond_latent,
            speaker_embedding,
            speed=1.2,
            temperature=0.65,
            repetition_penalty=5.0,
            #top_k=50,
            #top_p=0.85,
            #length_penalty=1.0,
            #enable_text_splitting=True,
        )

        audio = torch.tensor(result["wav"]).unsqueeze(0)  # inference() returns a numpy array under "wav"
        
        chunk_file = f"{output_file}_{i}.wav"
        torchaudio.save(chunk_file, audio, 24000)

        audios.append(audio)
        yield f"event: chunk\ndata: {chunk_file}\n\n"

    full_audio = torch.cat(audios, dim=1)
    final_file = f"{output_file}.wav"
    await asyncio.to_thread(torchaudio.save, final_file, full_audio, 24000)

    yield f"event: done\ndata: {final_file}\n\n"