from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

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

# Dynamically include capability endpoints if they exist
api_dir = Path(__file__).parent / "api"

image_routes = api_dir / "image_routes.py"
if image_routes.exists():
    try:
        from backend.app.api.image_routes import router as image_router
        app.include_router(image_router)
        print("✅ Image generation endpoints loaded")
    except Exception as e:
        print(f"⚠️  Could not load image routes: {e}")

video_routes = api_dir / "video_routes.py"
if video_routes.exists():
    try:
        from backend.app.api.video_routes import router as video_router
        app.include_router(video_router)
        print("✅ Video generation endpoints loaded")
    except Exception as e:
        print(f"⚠️  Could not load video routes: {e}")
