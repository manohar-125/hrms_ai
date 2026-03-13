from fastapi import FastAPI

from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router

app = FastAPI(title="HRMS AI Service")

app.include_router(chat_router)
app.include_router(health_router)