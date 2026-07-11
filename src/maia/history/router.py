import os
import httpx2
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from maia.logging_config import logger
from maia.templating import templates

router = APIRouter()

GATEWAY_URL = os.getenv("HERMES_GATEWAY_URL")
GATEWAY_APIKEY = os.getenv("HERMES_GATEWAY_APIKEY")

@router.get("/sessions")
async def load_sessions(request: Request):

    headers = {
        "Authorization": f"Bearer {GATEWAY_APIKEY}",
        "Content-Type": "application/json",
    }

    offset = request.query_params.get("offset", 0)

    async with httpx2.AsyncClient(timeout=None) as client:
        
        try:
            response = await client.get(
                f"{GATEWAY_URL}/api/sessions",
                headers=headers,
                params={"offset": offset}
            )
            response.raise_for_status() 
            result = response.json()
            print(f"Loaded sessions: {len(result.get('data', []))}")  # Debugging line
            return templates.TemplateResponse(request=request, name="parts/sessions_list.html", context={"result": result})
        except Exception as e:
            logger.error(f"Unexpected error in load_sessions: {str(e)}", exc_info=True)
            return templates.TemplateResponse(request=request, name="parts/sessions_list.html", context={"result": {"data": [], "has_more": False}})