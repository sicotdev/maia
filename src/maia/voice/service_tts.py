import asyncio
import torch
import scipy.io.wavfile
import os.path
from pocket_tts import TTSModel, export_model_state
from pathlib import Path

# Directory the current .py file lives in
BASE_DIR = Path(__file__).resolve().parent

# Load model with wav file (todo: export safetensors)
model_wav_path = BASE_DIR / "pocket-models" / "estelle.wav"
model_tensor_path = BASE_DIR / "pocket-models" / "estelle.safetensors"


# Higher quality (more steps)
#temp=0.5, lsd_decode_steps=5

# More expressive (higher temperature)
#temp=1.0

# Adjust EOS threshold, smaller means finishing earlier.
#eos-threshold=-3.0 --> cause short answers to be cut sometimes
# adding . at the end of chunks helped, but not fixed totally

# Load the model
tts_model = TTSModel.load_model( 
    language="french_24l", temp=0.9, lsd_decode_steps=5, eos_threshold=-3.0
)

# Get voice state
#voice_state = tts_model.get_state_for_audio_prompt(model_wav_path)
voice_state = tts_model.get_state_for_audio_prompt(model_tensor_path)

# Export to safetensors after loaded from wav for fast loading later
#export_model_state(voice_state, model_tensor_path)

#TODO
# Stream generation
#for chunk in model.generate_audio_stream(voice_state, "Long text content..."):    
    # Process each chunk as it's generated
    #print(f"Generated chunk: {chunk.shape[0]} samples")
    
    # Could save chunks to file or play in real-time


async def generate_audio(text: str, output_file: str): 

    if (os.path.isfile(f"{output_file}.wav")):
        yield f"event: done\ndata: {output_file}.wav\n\n"
        return

    # Split ignoring empty chunk
    chunks = [chunk.strip() for chunk in text.split('\n') if chunk.strip()]
    audios = []
    length = len(chunks)
    for i, chunk in enumerate(chunks):
        print(f'GENERATING {i+1}/{length}: {chunk}')

        # run the blocking TTS call in a thread so it doesn't block the event loop
        audio = await asyncio.to_thread(  
            tts_model.generate_audio, voice_state, f"{chunk}." #add trailing .
        )
        print(f"Generated audio shape: {audio.shape}")
        print(f"Audio duration: {audio.shape[-1] / tts_model.sample_rate:.2f} seconds")

        audios.append(audio)
        chunk_file = f"{output_file}_{i}.wav"
        scipy.io.wavfile.write(chunk_file, tts_model.sample_rate, audio.numpy())
        yield f"event: chunk\ndata: {chunk_file}\n\n"

    # Concatenate all audio
    full_audio = torch.cat(audios, dim=0)
    await asyncio.to_thread(
        scipy.io.wavfile.write, f"{output_file}.wav", tts_model.sample_rate, full_audio.numpy()
    )

    yield f"event: done\ndata: {output_file}.wav\n\n"