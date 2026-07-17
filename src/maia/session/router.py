import httpx2
import time
from fastapi import APIRouter, Request
from maia.gateway import GATEWAY_URL, get_gateway_headers
from maia.logging_config import logger
from maia.templating import templates

router = APIRouter()

@router.get("")
async def load_sessions(request: Request):
    
    offset = request.query_params.get("offset", 0)
    filter_text = request.query_params.get("filter-text", "").lower()
    filter_date = request.query_params.get("filter-date", "all")

    async with httpx2.AsyncClient(timeout=None) as client:
        try:
            response = await client.get(
                f"{GATEWAY_URL}/api/sessions",
                headers=get_gateway_headers(),
                params={"offset": offset}
            )
            response.raise_for_status() 
            result = response.json()
            
            data = result.get("data", [])
            
            filtered_data = []
            now = time.time()
            
            for session in data:
                preview = session.get("preview", "").lower()
                
                # Text filter: if filter_text exists, preview must contain it
                if filter_text and filter_text not in preview:
                    continue
                
                # Date filter
                started_at = session.get("started_at")
                if started_at and filter_date != "all":
                    try:
                        ts = float(started_at)
                        is_in_range = False
                        
                        if filter_date == "today":
                            is_in_range = (now - 86400 <= ts <= now)
                        elif filter_date == "week":
                            is_in_range = (now - 604800 <= ts <= now)
                        elif filter_date == "month":
                            is_in_range = (now - 2592000 <= ts <= now)
                            
                        if not is_in_range:
                            continue
                    except (ValueError, TypeError):
                        continue

                filtered_data.append(session)
            
            result["data"] = filtered_data
            print(f"Loaded {len(data)} sessions, {len(filtered_data)} after filtering.")
            
            return templates.TemplateResponse(request=request, name="session/sessions.html", context={"result": result, "filter_text": filter_text, "filter_date": filter_date})
        except Exception as e:
            logger.error(f"Unexpected error in load_sessions: {str(e)}", exc_info=True)
            return templates.TemplateResponse(request=request, name="session/sessions.html", context={"result": {"data": [], "has_more": False}})