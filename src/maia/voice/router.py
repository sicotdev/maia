from fastapi import APIRouter, UploadFile, File, HTTPException
from maia.voice.service import transcribe_audio
import shutil
import os
import uuid

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
