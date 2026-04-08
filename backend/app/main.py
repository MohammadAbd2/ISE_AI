from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.api.routes import router
from app.api.evolution_routes import evolution_router
from app.core.config import settings


# Keep FastAPI setup minimal here and move real logic into routes/services.
app = FastAPI(
    title=settings.app_name,
    version="0.3.0",  # Updated version with project awareness
    description="Local AI chatbot backend with agent-oriented architecture, project awareness, and self-evolution capabilities.",
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

# Include project analysis routes
try:
    from app.api.project_routes import router as project_router
    app.include_router(project_router)
    print("✅ Project analysis endpoints loaded")
except Exception as e:
    print(f"⚠️  Could not load project routes: {e}")

# Include enhanced feature routes
try:
    from app.api.enhanced_routes import router as enhanced_router
    app.include_router(enhanced_router, prefix="")
    print("✅ Enhanced API endpoints loaded (Terminal, Git, RAG, Voice, etc.)")
except Exception as e:
    print(f"⚠️  Could not load enhanced routes: {e}")

# Include FileSystem Plugin routes
try:
    from app.api.filesystem_routes import router as filesystem_router
    app.include_router(filesystem_router)
    print("✅ FileSystem Plugin endpoints loaded (Advanced file system introspection)")
except Exception as e:
    print(f"⚠️  Could not load FileSystem Plugin routes: {e}")

# Dynamically include capability endpoints if they exist
api_dir = Path(__file__).parent / "api"

image_routes = api_dir / "image_routes.py"
if image_routes.exists():
    try:
        from app.api.image_routes import router as image_router
        app.include_router(image_router)
        print("✅ Image generation endpoints loaded")
    except Exception as e:
        print(f"⚠️  Could not load image routes: {e}")

video_routes = api_dir / "video_routes.py"
if video_routes.exists():
    try:
        from app.api.video_routes import router as video_router
        app.include_router(video_router)
        print("✅ Video generation endpoints loaded")
    except Exception as e:
        print(f"⚠️  Could not load video routes: {e}")

# Include self-learning and planning routes
learning_routes = api_dir / "learning_routes.py"
if learning_routes.exists():
    try:
        from app.api.learning_routes import router as learning_router
        app.include_router(learning_router)
        print("✅ Self-learning and planning endpoints loaded")
    except Exception as e:
        print(f"⚠️  Could not load learning routes: {e}")

# Include multi-agent routes
agent_routes = api_dir / "agent_routes.py"
if agent_routes.exists():
    try:
        from app.api.agent_routes import router as agent_router
        app.include_router(agent_router)
        print("✅ Multi-agent orchestration endpoints loaded")
    except Exception as e:
        print(f"⚠️  Could not load agent routes: {e}")

# Include project indexing routes
try:
    from app.api.project_indexing_routes import router as project_indexing_router
    app.include_router(project_indexing_router)
    print("✅ Project indexing endpoints loaded (Fast filesystem queries)")
except Exception as e:
    print(f"⚠️  Could not load project indexing routes: {e}")

# Include Git integration routes
try:
    from app.api.git_routes import router as git_router
    app.include_router(git_router)
    print("✅ Git integration endpoints loaded (status, commit, branch, push, pull, log, blame)")
except Exception as e:
    print(f"⚠️  Could not load git routes: {e}")

# Include Terminal routes
try:
    from app.api.terminal_routes import router as terminal_router
    app.include_router(terminal_router)
    print("✅ Terminal integration endpoints loaded (run commands, error analysis)")
except Exception as e:
    print(f"⚠️  Could not load terminal routes: {e}")

# Include Semantic Search routes
try:
    from app.api.search_routes import router as search_router
    app.include_router(search_router)
    print("✅ Semantic code search endpoints loaded")
except Exception as e:
    print(f"⚠️  Could not load search routes: {e}")

# Include MCP routes
try:
    from app.api.mcp_routes import router as mcp_router
    app.include_router(mcp_router)
    print("✅ MCP (Model Context Protocol) endpoints loaded")
except Exception as e:
    print(f"⚠️  Could not load MCP routes: {e}")

# Include LSP routes
try:
    from app.api.lsp_routes import router as lsp_router
    app.include_router(lsp_router)
    print("✅ LSP (Language Server Protocol) endpoints loaded")
except Exception as e:
    print(f"⚠️  Could not load LSP routes: {e}")

# Include Collaboration routes
try:
    from app.api.collaboration_routes import router as collab_router
    app.include_router(collab_router)
    print("✅ Real-time collaboration endpoints loaded")
except Exception as e:
    print(f"⚠️  Could not load collaboration routes: {e}")

# Include Browser routes
try:
    from app.api.browser_routes import router as browser_router
    app.include_router(browser_router)
    print("✅ Embedded browser endpoints loaded")
except Exception as e:
    print(f"⚠️  Could not load browser routes: {e}")
