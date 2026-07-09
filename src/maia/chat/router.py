import os
import httpx2
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from maia.logging_config import logger

router = APIRouter()

GATEWAY_URL = os.getenv("HERMES_GATEWAY_URL")
GATEWAY_APIKEY = os.getenv("HERMES_GATEWAY_APIKEY")


@router.post("/chat")
async def chat(request: Request):
    data = await request.form()
    user_message = data.get("message")

    if not user_message:
        raise HTTPException(status_code=400, detail="No message provided")

    headers = {
        "Authorization": f"Bearer {GATEWAY_APIKEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "hermes-llm",
        "messages": [{"role": "user", "content": user_message}],
    }

    async with httpx2.AsyncClient(timeout=None) as client:
        error_message = "Une erreur est survenue, veuillez nous excuser pour la gêne occasionnée."

        try:
            response = await client.post(
                f"{GATEWAY_URL}/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            result = response.json()

            ai_response = result["choices"][0]["message"]["content"]

            return JSONResponse(
                {
                    "role": "assistant",
                    "content": ai_response,
                    "error": False,
                }
            )

        except httpx2.HTTPStatusError as e:
            logger.error(
                f"Gateway HTTP Error: {e.response.status_code} - {e.response.text}",
                exc_info=True,
            )
            return JSONResponse(
                {
                    "role": "assistant",
                    "content": error_message,
                    "error": True,
                }
            )
        except Exception as e:
            logger.error(f"Unexpected error in chat router: {str(e)}", exc_info=True)
            return JSONResponse(
                {
                    "role": "assistant",
                    "content": error_message,
                    "error": True,
                }
            )
