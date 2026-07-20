import asyncio
import soundfile as sf
import torch
import os.path
from pocket_tts import TTSModel, export_model_state
from maia.voice.classes.tts_engine import TTSEngine
from maia.config.settings import VOICES, VOICE_SAMPLES_DIR

class PocketTTS(TTSEngine):
    def __init__(self):

        # Higher quality (more steps)
        #temp=0.5, lsd_decode_steps=5

        # More expressive (higher temperature)
        #temp=1.0

        # Adjust EOS threshold, smaller means finishing earlier.
        #eos-threshold=-3.0 --> cause short answers to be cut sometimes
        # adding . at the end of chunks helped, but not fixed totally
        # frames_after_eos = 2 helped too for end hallucination

        # Load the model
        self.tts_model = TTSModel.load_model( 
            language="french_24l", temp=0.6, lsd_decode_steps=5, eos_threshold=-2.5
        )

        # Init voice states
        self.voice_states = []
        for voice in VOICES:
            model_wav_path = f"{VOICE_SAMPLES_DIR}/{voice['id']}.wav"
            model_tensor_path = f"{VOICE_SAMPLES_DIR}/{voice['id']}.safetensors"

            # Get voice state
            if (os.path.isfile(model_tensor_path)):
                print(f"Loading tensor file for {voice['id']}")
                voice_state = self.tts_model.get_state_for_audio_prompt(model_tensor_path)
            else:
                print(f"Loading wav file for {voice['id']}")
                # Export to safetensors after loaded from wav for fast loading later
                voice_state = self.tts_model.get_state_for_audio_prompt(model_wav_path)    
                export_model_state(voice_state, model_tensor_path)
            
            # Store voice state
            self.voice_states.append(voice_state)

    #Generate one wav file
    def generate_audio(self, text: str, output_file: str, voice: int): 
        print(f'GENERATING {output_file}: {text}')

        audio = self.tts_model.generate_audio(self.voice_states[voice], f"{text}", frames_after_eos=2)
       
        sf.write(output_file, audio, self.tts_model.sample_rate)


    #Generate chunks, yield sse event
    async def generate_audio_stream(self, text: str, output_name: str, output_dir: str, tmp_dir: str, voice: int): 

        # Split ignoring empty chunk
        chunks = [chunk.strip() for chunk in text.split('\n') if chunk.strip()]
        audios = []
        length = len(chunks)
        i = 0
        retry = False # used to retry once if epic fail
        while i < len(chunks):
            chunk = chunks[i]
            print(f'GENERATING {i+1}/{length}: {chunk}')

            # run the blocking TTS call in a thread so it doesn't block the event loop
            audio = await asyncio.to_thread(  
                self.tts_model.generate_audio, self.voice_states[voice], f"{chunk}", frames_after_eos=2
            )
            
            #check for epic fail
            if TTSEngine.is_epic_fail(audio):
                if not retry:
                    printf('NOISE DETECTED')
                    retry = True
                    continue # retry once
                else:
                    printf('NOISE DETECTED A SECOND TIME')
                    audio = torch.zeros_like(audio)

            audios.append(audio)
            chunk_file = f"{tmp_dir}/{output_name}_{i}.wav"
            
            retry = False
            i += 1
          
            await asyncio.to_thread(self._write_wav, chunk_file, audio, self.tts_model.sample_rate)

            yield f"event: chunk\ndata: {chunk_file}\n\n"

        # Concatenate all audio
        full_audio = torch.cat(audios, dim=0)
        final_file = f"{output_dir}/{output_name}.wav"
        await asyncio.to_thread(
            self._write_wav, final_file, full_audio, self.tts_model.sample_rate
        )

        yield f"event: done\ndata: {final_file}\n\n"

    @staticmethod
    def _write_wav(file: str, audio: torch.Tensor, samplerate: int) -> None:
        sf.write(file, audio, samplerate)
        TTSEngine.normalize_audio(file, file)