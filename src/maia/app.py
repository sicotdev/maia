from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import uvicorn
import os
import argparse

# Import the logging config first
from maia.logging_config import setup_logging
setup_logging()

# Now import the chat router and logger
from maia.chat.router import router as chat_router
from maia.logging_config import logger

# Load environment variables
load_dotenv()

# Launch app
app = FastAPI(title="Maia Gateway")

# Setup templates and static files
templates = Jinja2Templates(directory="templates")

# Mount static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(chat_router)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

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
