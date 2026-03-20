from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router

app = FastAPI(title="HRMS AI Service")

# Include API routers
app.include_router(chat_router)
app.include_router(health_router)

# Serve static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Serve index.html at root
@app.get("/")
async def serve_root():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "HRMS AI Service is running"}