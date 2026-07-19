import asyncio
import torch
import scipy.io.wavfile
import os.path
from pocket_tts import TTSModel, export_model_state
from pathlib import Path
from maia.settings import VOICES

# Directory the current .py file lives in
BASE_DIR = Path(__file__).resolve().parent

DEFAULT_VOICE = 0

# Higher quality (more steps)
#temp=0.5, lsd_decode_steps=5

# More expressive (higher temperature)
#temp=1.0

# Adjust EOS threshold, smaller means finishing earlier.
#eos-threshold=-3.0 --> cause short answers to be cut sometimes
# adding . at the end of chunks helped, but not fixed totally
# frames_after_eos = 2 helped too for end hallucination


# Load the model
tts_model = TTSModel.load_model( 
    language="french_24l", temp=0.6, lsd_decode_steps=5, eos_threshold=-2.5
)

VOICES_STATES = []
for voice in VOICES:
    model_wav_path = BASE_DIR / "pocket-models" / f"{voice['id']}.wav"
    model_tensor_path = BASE_DIR / "pocket-models" / f"{voice['id']}.safetensors"

    # Get voice state
    if (os.path.isfile(model_tensor_path)):
        print(f"Loading tensor file for {voice['id']}")
        voice_state = tts_model.get_state_for_audio_prompt(model_tensor_path)
    else:
        print(f"Loading wav file for {voice['id']}")
        # Export to safetensors after loaded from wav for fast loading later
        voice_state = tts_model.get_state_for_audio_prompt(model_wav_path)    
        export_model_state(voice_state, model_tensor_path)
    
    # Store voice state
    VOICES_STATES.append(voice_state)


#Generate one wav file
def generate_audio(text: str, output_file: str, voice: int = DEFAULT_VOICE): 
    print(f'GENERATING {output_file}: {text}')

    audio = tts_model.generate_audio(VOICES_STATES[voice], f"{text}", frames_after_eos=2)
    
    print(f"Generated audio shape: {audio.shape}")
    print(f"Audio duration: {audio.shape[-1] / tts_model.sample_rate:.2f} seconds")

    scipy.io.wavfile.write(output_file, tts_model.sample_rate, audio.numpy())


#Generate chunks, yield sse event
async def generate_audio_stream(text: str, output_name: str, output_dir: str, tmp_dir: str, voice: int = DEFAULT_VOICE): 

    # Split ignoring empty chunk
    chunks = [chunk.strip() for chunk in text.split('\n') if chunk.strip()]
    audios = []
    length = len(chunks)
    for i, chunk in enumerate(chunks):
        print(f'GENERATING {i+1}/{length}: {chunk}')

        # run the blocking TTS call in a thread so it doesn't block the event loop
        audio = await asyncio.to_thread(  
            tts_model.generate_audio, VOICES_STATES[voice], f"{chunk}", frames_after_eos=2
        )
        print(f"Generated audio shape: {audio.shape}")
        print(f"Audio duration: {audio.shape[-1] / tts_model.sample_rate:.2f} seconds")

        audios.append(audio)
        chunk_file = f"{tmp_dir}/{output_name}_{i}.wav"
        scipy.io.wavfile.write(chunk_file, tts_model.sample_rate, audio.numpy())
        yield f"event: chunk\ndata: {chunk_file}\n\n"

    # Concatenate all audio
    full_audio = torch.cat(audios, dim=0)
    await asyncio.to_thread(
        scipy.io.wavfile.write, f"{output_dir}/{output_name}.wav", tts_model.sample_rate, full_audio.numpy()
    )

    yield f"event: done\ndata: {output_dir}/{output_name}.wav\n\n"