import soundfile as sf
import asyncio
import torch
import os.path
from kokoro import KPipeline
from maia.voice.classes.tts_engine import TTSEngine

class KokoroTTS(TTSEngine):
    def __init__(self):
        self.pipeline = KPipeline(lang_code='f')

    #Generate one wav file
    def generate_audio(self, text: str, output_file: str, voice: int): 

        generator = self.pipeline(
                text, voice='ff_siwis', # <= change voice here
                speed=1, split_pattern=r'\n+'
            )

        audios = []

        for i, (gs, ps, audio) in enumerate(generator):
            
            print(i, gs, ps)

            audios.append(audio)

        # Concatenate all audio
        full_audio = torch.cat(audios, dim=0)
        sf.write(output_file, full_audio, 24000)

    #Generate chunks, yield sse event
    async def generate_audio_stream(self, text: str, output_name: str, output_dir: str, tmp_dir: str, voice: int): 

        generator = self.pipeline(
            text, voice='ff_siwis', # <= change voice here (only one FR voice)
            speed=1, split_pattern=r'\n+'
        )

        audios = []
        i = 0
        while True:
            # run the blocking `next()` call in a thread; None = sentinel for StopIteration
            item = await asyncio.to_thread(next, generator, None)
            if item is None:
                break        
                
            gs, ps, audio = item
            print(i, gs, ps)
            
            #display(Audio(data=audio, rate=24000, autoplay=i==0))

            audios.append(audio)

            chunk_file = f"{tmp_dir}/{output_name}_{i}.wav"
            await asyncio.to_thread(self._write_wav, chunk_file, audio)
            
            yield f"event: chunk\ndata: {chunk_file}\n\n"

            i += 1

        # Concatenate all audio
        full_audio = torch.cat(audios, dim=0)
        final_file = f"{output_dir}/{output_name}.wav"

        await asyncio.to_thread(self._write_wav, final_file, full_audio)
        
        yield f"event: done\ndata: {final_file}\n\n"

    @staticmethod
    def _write_wav(file: str, audio: torch.Tensor):
        sf.write(file, audio, 24000)
        TTSEngine.normalize_audio(file, file)