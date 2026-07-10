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
    # Optionnel : pour enchaîner les tours d'une même conversation sans
    # renvoyer tout l'historique toi-même. Stocke cette valeur côté client
    # (session/cookie) et renvoie-la au tour suivant.
    previous_response_id = data.get("previous_response_id")
 
    if not user_message:
        raise HTTPException(status_code=400, detail="No message provided")
 
    headers = {
        "Authorization": f"Bearer {GATEWAY_APIKEY}",
        "Content-Type": "application/json",
    }
 
    payload = {
        "model": "hermes-llm",
        "input": user_message,
        "store": True,  # nécessaire pour pouvoir chaîner via previous_response_id
    }
    if previous_response_id:
        payload["previous_response_id"] = previous_response_id
 
    async with httpx2.AsyncClient(timeout=None) as client:
        error_message = "Une erreur est survenue, veuillez nous excuser pour la gêne occasionnée."
 
        try:
            response = await client.post(
                f"{GATEWAY_URL}/v1/responses",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            result = response.json()
 
            tool_steps = []
            ai_response = ""
 
            for item in result.get("output", []):
                item_type = item.get("type")
 
                if item_type == "function_call":
                    tool_steps.append(
                        {
                            "type": "tool_call",
                            "name": item.get("name"),
                            "arguments": item.get("arguments"),
                            "call_id": item.get("call_id"),
                        }
                    )
                elif item_type == "function_call_output":
                    tool_steps.append(
                        {
                            "type": "tool_result",
                            "call_id": item.get("call_id"),
                            "output": item.get("output"),
                        }
                    )
                elif item_type == "message":
                    for content_part in item.get("content", []):
                        if content_part.get("type") == "output_text":
                            ai_response += content_part.get("text", "")
 
            return JSONResponse(
                {
                    "role": "assistant",
                    "content": ai_response,
                    "tool_steps": tool_steps,  # à afficher côté front comme des "cartes" de progression
                    "response_id": result.get("id"),  # à renvoyer au tour suivant comme previous_response_id
                    "usage": result.get("usage", {}),
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