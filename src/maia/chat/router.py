import httpx2
from fastapi import APIRouter, Request, HTTPException
import os
from maia.logging_config import setup_logging, logger



router = APIRouter()

GATEWAY_URL = os.getenv("HERMES_GATEWAY_URL")
GATEWAY_APIKEY = os.getenv("HERMES_GATEWAY_APIKEY")

@router.post("/chat")
async def chat(request: Request):
    # Get message from request body (HTMX/Form data)
    data = await request.form()
    user_message = data.get("message")
    
    if not user_message:
        raise HTTPException(status_code=400, detail="No message provided")

    # Call Hermes Gateway
    # We'll assume a standard OpenAI-compatible structure for the gateway
    headers = {
        "Authorization": f"Bearer {GATEWAY_APIKEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "hermes-llm", # Default or configurable
        "messages": [
            {"role": "user", "content": user_message}
        ]
    }

    async with httpx2.AsyncClient(timeout=None) as client:
        try:
            response = await client.post(
                f"{GATEWAY_URL}/v1/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            
            # Extract the AI response text
            ai_response = result["choices"][0]["message"]["content"]
            
            # Return a simple HTML snippet for HTMX to inject
            # We wrap it in a div with the correct class
            return f'<div class="message ai-message">{ai_response}</div>'
            
        except httpx2.HTTPStatusError as e:
            logger.error(f"DEBUG_LOG_TEST: Gateway HTTP Error: {e.response.status_code} - {e.response.text}", exc_info=True)
            logger.info("Attempting to write to log file...")
            return '<div class="message ai-message">Une erreur est survenue, veuillez nous excuser pour la gêne occasionnée.</div>'
        except Exception as e:
            logger.error(f"Unexpected error in chat router: {str(e)}", exc_info=True)
            return '<div class="message ai-message">Une erreur est survenue, veuillez nous excuser pour la gêne occasionnée.</div>'
