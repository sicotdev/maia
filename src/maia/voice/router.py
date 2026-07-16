from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from maia.voice.service_stt import transcribe_audio
#from maia.voice.service_cosyvoice_tts import generate_audio
#from maia.voice.service_kokoro_tts import generate_audio
from maia.voice.service_pocket_tts import generate_audio
#from maia.voice.service_coqui_x_tts import generate_audio
from maia.logging_config import logger
import emoji
import shutil
import os
import uuid
import re

#Where wav files are generated: 
#TODO: clean this dir sometimes
OUTPUT_DIR = "static/wav"

router = APIRouter(prefix="/v1/voice", tags=["voice"])

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
async def generate(request: Request):
    message_id = request.query_params.get("message_id")
    text = request.query_params.get("text")

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

    #Test:
    #text = text.replace('Intelligence', "intelligence.")

    output_file = f"{OUTPUT_DIR}/{message_id}"

    return StreamingResponse(
        generate_audio(text, output_file),
        media_type="text/event-stream",
    )