
from kokoro import KPipeline
#from IPython.display import display, Audio
import soundfile as sf
import asyncio
import torch
import os.path

pipeline = KPipeline(lang_code='f')


#text = 'Le dromadaire resplendissant déambulait tranquillement dans les méandres en mastiquant de petites feuilles vernissées.'



async def generate_audio(text: str, output_file: str): 

    if (os.path.isfile(f"{output_file}.wav")):
        yield f"event: done\ndata: {output_file}.wav\n\n"
        return

    generator = pipeline(
        text, voice='ff_siwis', # <= change voice here
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
        chunk_file = f"{output_file}_{i}.wav"
        sf.write(chunk_file, audio, 24000)
        yield f"event: chunk\ndata: {chunk_file}\n\n"

        i += 1

    # Concatenate all audio
    full_audio = torch.cat(audios, dim=0)
    await asyncio.to_thread(
        sf.write, f"{output_file}.wav", full_audio, 24000
    )

    yield f"event: done\ndata: {output_file}.wav\n\n"