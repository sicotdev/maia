import os
from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import HTMLResponse

from maia.templating import templates

from maia.chat.router import router as chat_router
from maia.session.router import router as session_router
from maia.voice.router import router as voice_router
from maia.settings.router import router as settings_router

main_router = APIRouter()
main_router.include_router(chat_router, prefix="/chat", tags=["chat"])
main_router.include_router(session_router, prefix="/sessions", tags=["session"])
main_router.include_router(voice_router, prefix="/v1/voice", tags=["voice"])
main_router.include_router(settings_router, prefix="/settings", tags=["settings"])

# Serve index.html at the root path
@main_router.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"DEBUG": os.getenv("DEBUG", "False") == "True"})

