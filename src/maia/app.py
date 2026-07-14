from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from maia.templating import templates
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import uvicorn
import os
import argparse

# Load environment variables
load_dotenv()

# Launch app
app = FastAPI(title="Maia Gateway")

# Mount static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
from maia.chat.router import router as chat_router
from maia.session.router import router as session_router
from maia.voice.router import router as voice_router
app.include_router(chat_router)
app.include_router(session_router)
app.include_router(voice_router)

# Serve index.html at the root path
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"DEBUG": os.getenv("DEBUG", "False") == "True"})


# This is what 'uv run maia' calls
def main():

    # Parse arguments for host, port, and reload
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8645)))
    parser.add_argument("--host", type=str, default=os.environ.get("HOST", "0.0.0.0"))
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    # Run the Uvicorn server with the specified host, port, and reload option
    port = args.port
    uvicorn.run("maia.app:app", host=args.host, port=port, reload=args.reload)

if __name__ == "__main__":
    main()
