import shutil
import os
import uuid
import asyncio
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import Response, StreamingResponse

from maia.voice.service_stt import transcribe_audio
from maia.voice.service_tts import generate_audio, merge_audio, generate_audio_stream


FORCE_RELOAD_WAV = os.getenv("DEBUG") or False

# Where wav files are generated:
# TODO: clean this dir sometimes
OUTPUT_DIR = "static/wav"
TMP_DIR = f"{OUTPUT_DIR}/tmp"

# Clean tmp dir (containing wav chunks)
if os.path.exists(TMP_DIR):
    shutil.rmtree(TMP_DIR)
Path(TMP_DIR).mkdir(parents=True, exist_ok=True)

router = APIRouter()


@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    # Generate a unique filename to avoid collisions
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing file")

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

        return {"status": "success", "text": text}
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
    text: str = Query(..., min_length=1),
):

    output_file = f"{OUTPUT_DIR}/{message_id}"

    # We already have the output file
    if not FORCE_RELOAD_WAV and os.path.isfile(f"{output_file}.wav"):
        return Response(
            content=f"event: done\ndata: {output_file}.wav\n\n",
            media_type="text/event-stream",
        )

    return StreamingResponse(
        generate_audio_stream(engine, text, message_id, OUTPUT_DIR, TMP_DIR, voice),
        media_type="text/event-stream",
    )


@router.get("/generate_chunk")
async def generate_chunk(
    engine: int = Query(..., ge=0),
    voice: int = Query(..., ge=0),
    message_id: str = Query(..., min_length=1),
    text: str = Query(..., min_length=1),
    chunk_index: int = Query(..., ge=0),
):

    output_file = f"{TMP_DIR}/{message_id}_{chunk_index}.wav"

    await asyncio.to_thread(generate_audio, engine, text, output_file, voice)

    return {"audio": output_file}


@router.get("/merge_chunks")
async def merge_chunks(
    tmp_id: str = Query(..., min_length=1),
    message_id: str = Query(..., min_length=1),
    chunk_length: int = Query(..., ge=1),
):

    chunk_files = [f"{TMP_DIR}/{tmp_id}_{i}.wav" for i in range(chunk_length)]
    output_file = f"{OUTPUT_DIR}/{message_id}.wav"

    await asyncio.to_thread(merge_audio, chunk_files, output_file)

    return {"audio": output_file}
