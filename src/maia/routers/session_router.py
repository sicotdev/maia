import time

import httpx2
from fastapi import APIRouter, Depends, Form, Path, Query, Request, Response
from fastapi.responses import JSONResponse

from maia.config.gateway import get_gateway_params
from maia.config.logging_config import logger
from maia.config.templating import templates
from maia.routers.chat_router import generate_summary_title

router = APIRouter()


@router.get("")
async def load_sessions(
    request: Request,
    gateway_params: str = Depends(get_gateway_params),
    offset: int = Query(0),
    filter_text: str = Query(""),
    filter_date: str = Query("all"),
):
    filter_date = filter_date or "all"  # empty becomes 'all'

    print(f"Loading sessions from {gateway_params['url']}")

    async with httpx2.AsyncClient(timeout=None) as client:
        try:
            response = await client.get(
                f"{gateway_params['url']}/api/sessions",
                headers=gateway_params["headers"],
                params={"offset": offset},
            )
            response.raise_for_status()
            result = response.json()

            data = result.get("data", [])

            filtered_data = []
            now = time.time()

            for session in data:
                title = session.get("title")
                if title:
                    session["preview"] = title

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

                        if filter_date == "j1":
                            is_in_range = ts <= (now - 86400)
                        elif filter_date == "j7":
                            is_in_range = ts <= (now - 604800)
                        elif filter_date == "j30":
                            is_in_range = ts <= (now - 2592000)

                        if not is_in_range:
                            continue
                    except (ValueError, TypeError):
                        continue

                filtered_data.append(session)

            result["data"] = filtered_data
            print(f"Loaded {len(data)} sessions, {len(filtered_data)} after filtering.")

            return templates.TemplateResponse(
                request=request,
                name="session/sessions.html",
                context={"result": result},
            )
        except httpx2.HTTPStatusError as e:
            logger.error(
                f"load_sessions HTTP Error: {e.response.status_code} - {e.response.text}",
                exc_info=True,
            )
            return templates.TemplateResponse(
                request=request,
                name="session/sessions.html",
                context={"result": {"data": [], "has_more": False}},
            )


@router.patch("/{session_id}/title")
async def update_session_title(
    request: Request,
    gateway_params: str = Depends(get_gateway_params),
    session_id: str = Path(...),
    title: str = Form(None),
    auto: bool = Form(False),
):
    print(f"Setting title to session {session_id}: {title} (auto={auto})")

    if auto:
        title = await generate_summary_title(gateway_params, session_id)

    print(f"Setting title: {title}")

    # Call update session
    async with httpx2.AsyncClient(timeout=None) as client:
        response = await client.patch(
            f"{gateway_params['url']}/api/sessions/{session_id}",
            headers=gateway_params["headers"],
            json={"title": title},
        )
        response.raise_for_status()
        result = response.json()

        # TODO: missing preview and last_active in response, we have to send only the new title instead of the whole object:
        session = result.get("session")
        print(session)

        session["preview"] = session["title"]

        return templates.TemplateResponse(
            request=request,
            name="session/session_oob.html",
            context={"session": session},
        )


async def _delete_session_api(
    gateway_params: str = Depends(get_gateway_params), session_id: str = Path(...)
):
    print(f"Deleting session {session_id}")
    async with httpx2.AsyncClient(timeout=None) as client:
        response = await client.delete(
            f"{gateway_params['url']}/api/sessions/{session_id}",
            headers=gateway_params["headers"],
        )
        response.raise_for_status()
        result = response.json()
        print(result)
    return Response(content="", media_type="text/html")


@router.delete("/batch-delete")
async def delete_sessions_bulk(
    gateway_params: str = Depends(get_gateway_params),
    session_ids: list[str] = Query(...),
):
    print(f"Deleting sessions: {session_ids}")
    deleted_ids = []
    for sid in session_ids:
        await _delete_session_api(gateway_params, sid)
        deleted_ids.append(sid)

    return JSONResponse(content={"successful": True, "ids": deleted_ids})


@router.delete("/{session_id}")
async def delete_session(
    gateway_params: str = Depends(get_gateway_params),
    session_id: str = Path(...),
):
    print(f"Deleting session: {session_id}")
    return await _delete_session_api(gateway_params, session_id)
