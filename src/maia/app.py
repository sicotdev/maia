from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import uvicorn
import os

# Load environment variables
load_dotenv()

app = FastAPI(title="Maia Gateway")

# Setup templates and static files
templates = Jinja2Templates(directory="templates")

# Mount static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/hello")
async def say_hello(request: Request):
    return "Hello from the backend! HTMX received this."

def main():
    # This is what 'uv run maia' calls
    # We use the module path 'maia.app:app'
    uvicorn.run("maia.app:app", host="0.0.0.0", port=8645, reload=True)

if __name__ == "__main__":
    main()
