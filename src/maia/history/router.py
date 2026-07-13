import httpx2
from fastapi import APIRouter, Request
from maia.gateway import GATEWAY_URL, get_gateway_headers
from maia.logging_config import logger
from maia.templating import templates

router = APIRouter()

@router.get("/sessions")
async def load_sessions(request: Request):

    offset = request.query_params.get("offset", 0)

    async with httpx2.AsyncClient(timeout=None) as client:
        
        try:
            response = await client.get(
                f"{GATEWAY_URL}/api/sessions",
                headers=get_gateway_headers(),
                params={"offset": offset}
            )
            response.raise_for_status() 
            result = response.json()
            print(f"Loaded sessions: {len(result.get('data', []))}")  # Debugging line
            return templates.TemplateResponse(request=request, name="session/sessions.html", context={"result": result})
        except Exception as e:
            logger.error(f"Unexpected error in load_sessions: {str(e)}", exc_info=True)
            return templates.TemplateResponse(request=request, name="session/sessions.html", context={"result": {"data": [], "has_more": False}})