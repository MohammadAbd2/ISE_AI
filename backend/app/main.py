from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import router
from backend.app.api.evolution_routes import evolution_router
from backend.app.core.config import settings


# Keep FastAPI setup minimal here and move real logic into routes/services.
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Local AI chatbot backend with agent-oriented architecture and self-evolution capabilities.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(evolution_router)
