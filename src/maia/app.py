import sys
from pathlib import Path

# NEEDED FOR CosyVoice
#TODO: clean this
BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(BASE_DIR))
sys.path.append(str(BASE_DIR / "third_party" / "Matcha-TTS"))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import uvicorn
import os
import argparse

from maia.routing import main_router

# Load environment variables
load_dotenv()

# Launch app
app = FastAPI(title="Maia Gateway")

# Mount static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Include router
app.include_router(main_router)


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
