import asyncio
import torch
import torchaudio
from typing import AsyncIterator
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
from maia.config.logging_config import logger

from maia.voice.classes.tts_engine import TTSEngine
from maia.config.settings import VOICES, VOICE_SAMPLES_DIR


class CoquiXTTS(TTSEngine):
    def __init__(self):

        # Required due to PyTorch 2.6+ weights_only default change
        torch.serialization.add_safe_globals([XttsConfig])

        XTTS_MODEL_DIR = "pretrained_models/xtts_v2"
        DEVICE = "cpu"  # Change to "cuda" if GPU is available
        logger.info(f"Loading xtts_v2 model on {DEVICE}...")

        config = XttsConfig()
        config.load_json(f"{XTTS_MODEL_DIR}/config.json")
        self.xtts_model = Xtts.init_from_config(config)
        self.xtts_model.load_checkpoint(
            config, checkpoint_dir=XTTS_MODEL_DIR, use_deepspeed=False
        )

        # TODO: install torch with cuda
        if DEVICE == "cuda":
            self.xtts_model.cuda()
        logger.info("Model loaded successfully.")

        self.voice_states = []
        for voice in VOICES:
            model_wav_path = f"{VOICE_SAMPLES_DIR}/{voice['id']}.wav"
            gpt_cond_latent, speaker_embedding = (
                self.xtts_model.get_conditioning_latents(
                    audio_path=[str(model_wav_path)]
                )
            )
            self.voice_states.append(
                {
                    "gpt_cond_latent": gpt_cond_latent,
                    "speaker_embedding": speaker_embedding,
                }
            )

    # Generate one wav file
    def generate_audio(self, text: str, output_file: str, voice: int):
        result = self.xtts_model.inference(
            text,
            "fr",
            self.voice_states[voice]["gpt_cond_latent"],
            self.voice_states[voice]["speaker_embedding"],
            speed=1.0,
            temperature=0.65,
            repetition_penalty=5.0,
            # top_k=50,
            # top_p=0.85,
            # length_penalty=1.0,
            # enable_text_splitting=True,
        )

        audio = torch.tensor(result["wav"]).unsqueeze(
            0
        )  # inference() returns a numpy array under "wav"
        torchaudio.save(output_file, audio, 24000)

    # Generate chunks, yield sse event
    async def generate_audio_stream(
        self, text: str, output_name: str, output_dir: str, tmp_dir: str, voice: int
    ) -> AsyncIterator[str]:

        # Split ignoring empty chunk
        chunks = [chunk.strip() for chunk in text.split("\n") if chunk.strip()]

        audios = []
        length = len(chunks)
        for i, chunk in enumerate(chunks):
            print(f"GENERATING {i + 1}/{length}: {chunk}")

            result = await asyncio.to_thread(
                self.xtts_model.inference,
                chunk,
                "fr",
                self.voice_states[voice]["gpt_cond_latent"],
                self.voice_states[voice]["speaker_embedding"],
                speed=1.2,
                temperature=0.65,
                repetition_penalty=5.0,
                # top_k=50,
                # top_p=0.85,
                # length_penalty=1.0,
                # enable_text_splitting=True,
            )

            audio = torch.tensor(result["wav"]).unsqueeze(
                0
            )  # inference() returns a numpy array under "wav"
            audios.append(audio)

            chunk_file = f"{tmp_dir}/{output_name}_{i}.wav"

            await asyncio.to_thread(self._write_wav, chunk_file, audio)

            yield f"event: chunk\ndata: {chunk_file}\n\n"

        full_audio = torch.cat(audios, dim=1)
        final_file = f"{output_dir}/{output_name}.wav"

        await asyncio.to_thread(self._write_wav, final_file, full_audio)

        yield f"event: done\ndata: {final_file}\n\n"

    @staticmethod
    def _write_wav(file: str, audio: torch.Tensor):
        torchaudio.save(file, audio, 24000)
        TTSEngine.normalize_audio(file, file)
