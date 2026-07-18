import emoji
import shutil
import os
import uuid
import re
import soundfile as sf
import numpy as np
import asyncio
import shutil
from pathlib import Path
from pydub import AudioSegment
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from maia.voice.service_stt import transcribe_audio
#from maia.voice.service_cosyvoice_tts import generate_audio, generate_audio_stream
#from maia.voice.service_kokoro_tts import generate_audio, generate_audio_stream
from maia.voice.service_pocket_tts import generate_audio, generate_audio_stream
#from maia.voice.service_coqui_x_tts import generate_audio, generate_audio_stream
from maia.logging_config import logger

#Where wav files are generated: 
#TODO: clean this dir sometimes
OUTPUT_DIR = "static/wav"

#Clean tmp dir (containing wav chunks)
if os.path.exists(f"{OUTPUT_DIR}/tmp"):
    shutil.rmtree(f"{OUTPUT_DIR}/tmp")

router = APIRouter()

def filter_text(text: str) -> str:
    #Remove emojis
    text = emoji.replace_emoji(text, replace='')

    #Replace file names with explicit "point" in french (and other few things)
    ext = {'.js': ' point JS', '.py': ' point pi', '.md': ' point MD',
            '.toml': ' point TOML',
            'TODO': 'tout doux', 'README': 'readme',
            ' & ': ' et ', ' :': ',',
            'backend': 'back-end', 'frontend': 'front-end', 
            'À': 'à', '/': ', '}
    for search, replaced in ext.items():
        text = re.sub(re.escape(search), replaced, text, flags=re.IGNORECASE)

    #Replace float numbers (ex: 12.5)
    regex = r"(\d+)\.(\d+)"
    replacement = r"\1 point \2"
    text = re.sub(regex, replacement, text)

    #Test:
    #text = text.replace('Intelligence', "intelligence.")
    return text

def normalize_audio(input_path, output_path):
    audio = AudioSegment.from_wav(input_path)
    # Normalise le volume à -1.0 dB
    normalized_audio = audio.normalize(-1.0)
    normalized_audio.export(output_path, format="wav")

@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    # Generate a unique filename to avoid collisions
    file_extension = os.path.splitext(file.filename)[1]
    if not file_extension:
        file_extension = ".wav"
    
    temp_filename = f"temp_voice_{uuid.uuid4()}{file_extension}"
    temp_path = os.path.abspath(temp_filename)

    try:
        # Save the uploaded file to a temporary location
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Call the transcription service
        text = transcribe_audio(temp_path)
        
        return {
            "status": "success",
            "text": text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.get("/generate")
async def generate(
    engine: int = Query(..., ge=0), 
    voice: int = Query(..., ge=0), 
    message_id: str = Query(..., min_length=1), 
    text: str = Query(..., min_length=1)
):

    text = filter_text(text)

    output_file = f"{OUTPUT_DIR}/{message_id}"

    #We already have the output file
    if (os.path.isfile(f"{output_file}.wav")):
        return Response(
            content=f"event: done\ndata: {output_file}.wav\n\n",
            media_type="text/event-stream",
        )

    Path(f"{OUTPUT_DIR}/tmp").mkdir(parents=True, exist_ok=True)

    return StreamingResponse(
        generate_audio_stream(text, message_id, OUTPUT_DIR, f"{OUTPUT_DIR}/tmp", voice),
        media_type="text/event-stream",
    )

@router.get("/generate_chunk")
async def generate_chunk(
    engine: int = Query(..., ge=0), 
    voice: int = Query(..., ge=0), 
    message_id: str = Query(..., min_length=1), 
    text: str = Query(..., min_length=1), 
    chunk_index: int = Query(..., ge=0)):

    text = filter_text(text)
    output_file = f"{OUTPUT_DIR}/tmp/{message_id}_{chunk_index}.wav"

    Path(f"{OUTPUT_DIR}/tmp").mkdir(parents=True, exist_ok=True)

    await asyncio.to_thread(  
        generate_audio, text, output_file, voice
    )

    normalize_audio(output_file, output_file)

    return {
        "audio": output_file
    }


@router.get("/merge_chunks")
async def merge_chunks(
    tmp_id: str = Query(..., min_length=1), 
    message_id: str = Query(..., min_length=1), 
    chunk_length: int = Query(..., ge=1)):

    chunk_files = [f"{OUTPUT_DIR}/tmp/{tmp_id}_{i}.wav" for i in range(chunk_length)]
    output_file = f"{OUTPUT_DIR}/{message_id}.wav"

    print(f"merging to: {output_file}")

    data_list = []
    samplerate = None
    subtype = None

    for filename in chunk_files:
        data, sr = sf.read(filename)
        if samplerate is None:
            samplerate = sr
            subtype = sf.info(filename).subtype
        elif sr != samplerate:
            raise ValueError(f"Sample rate mismatch in {filename}: {sr} != {samplerate}")
        data_list.append(data)

    merged = np.concatenate(data_list, axis=0)

    sf.write(output_file, merged, samplerate, subtype=subtype)

    normalize_audio(output_file, output_file)

    return {
        "audio": output_file
    }