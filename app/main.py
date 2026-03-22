from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import logging

from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router


logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

# Enable uvicorn access logs
logging.getLogger("uvicorn.access").setLevel(logging.INFO)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI(title="HRMS AI Service")

# Include API routers
app.include_router(chat_router)
app.include_router(health_router)

# Serve static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Serve chat UI at root
@app.get("/")
async def serve_root():
    chat_ui_path = os.path.join(static_dir, "chat-ui.html")
    if os.path.exists(chat_ui_path):
        return FileResponse(chat_ui_path)
    return {"message": "HRMS AI Service is running"}