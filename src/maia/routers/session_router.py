import httpx2
import time
from fastapi import APIRouter, Query, Request, Depends
from maia.gateway import get_gateway_url, get_gateway_headers
from maia.logging_config import logger
from maia.templating import templates

router = APIRouter()

@router.get("")
async def load_sessions(
    request: Request,
    gateway_url: str = Depends(get_gateway_url),
    offset: int = Query(0), 
    filter_text: str = Query(None), 
    filter_date: str = Query('all')
):
    filter_date = filter_date or "all" #empty becomes 'all'

    async with httpx2.AsyncClient(timeout=None) as client:
        try:
            response = await client.get(
                f"{gateway_url}/api/sessions",
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