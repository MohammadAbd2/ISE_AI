"""ISE AI — FastAPI backend entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.core.config import settings
from app.api.routes import router
from app.api.evolution_routes import evolution_router
from app.services.backup import get_backup_manager

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=(
        "ISE AI: Autonomous multi-agent coding assistant with hardware-aware model "
        "selection, self-improvement, web research, and sandboxed execution."
    ),
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

# Include plan dashboard endpoints (plan checkpoint listing & progress)
try:
    from app.api.plan_dashboard import router as plan_dashboard_router
    app.include_router(plan_dashboard_router)
    print("✅ Plan dashboard endpoints loaded")
except Exception as exc:
    print(f"⚠️ Could not load plan dashboard: {exc}")

# Hardware info endpoint at startup
@app.on_event("startup")
async def startup_event():
    from app.core.hardware import detect_hardware
    hw = detect_hardware()
    print(f"🖥️  Hardware: {hw.tier} tier | RAM {hw.available_ram_gb}/{hw.total_ram_gb} GB | "
          f"GPU {hw.gpu_vram_gb} GB | Model → {hw.recommended_model}")
    try:
        cleanup = get_backup_manager().cleanup_old_backups(max_age_days=30)
        print(f"🧹 Backup cleanup removed {len(cleanup.get('removed', []))} expired backups")
    except Exception as exc:
        print(f"⚠️  Backup cleanup skipped: {exc}")

_OPTIONAL_ROUTERS = [
    ("app.api.project_routes",         "router",                 "Project analysis"),
    ("app.api.enhanced_routes",        "router",                 "Enhanced API (Terminal, Git, RAG, Voice)"),
    ("app.api.filesystem_routes",      "router",                 "FileSystem Plugin"),
    ("app.api.image_routes",           "router",                 "Image generation"),
    ("app.api.learning_routes",        "router",                 "Self-learning and planning"),
    ("app.api.agent_routes",           "router",                 "Multi-agent orchestration"),
    ("app.api.project_indexing_routes","router",                 "Project indexing"),
    ("app.api.git_routes",             "router",                 "Git integration"),
    ("app.api.terminal_routes",        "router",                 "Terminal integration"),
    ("app.api.terminal_stream_routes", "router",                 "Real-time terminal streaming"),
    ("app.api.search_routes",          "router",                 "Semantic code search"),
    ("app.api.mcp_routes",             "router",                 "MCP (Model Context Protocol)"),
    ("app.api.lsp_routes",             "router",                 "LSP integration"),
    ("app.api.collaboration_routes",   "router",                 "Real-time collaboration"),
    ("app.api.browser_routes",         "router",                 "Embedded browser / computer-use"),
    ("app.api.hardware_routes",        "router",                 "Hardware info and model management"),
    ("app.api.dashboard_routes",       "router",                 "System Dashboard"),
    ("app.api.platform_routes",        "router",                 "Autonomous platform reliability/preview/trace"),
    ("app.api.elite_agi_routes",       "router",                 "Elite AGI roadmap/control plane"),
    ("app.api.real_intelligence_v2_routes", "router",          "Real Intelligence v2 execution/control"),
    ("app.api.agi_system_v3_routes", "router",              "AGI System v3 reasoning/evaluation/control"),
    ("app.api.agi_system_v4_routes", "router",              "AGI System v4 truth/reliability/control"),
    ("app.api.daily_programming_agi_routes", "router",      "Daily Programming AGI rebuild/control"),
    ("app.api.dynamic_agent_runtime_routes", "router",  "Dynamic no-template agent runtime"),
    ("app.api.programming_agi_routes", "router",              "Customer-grade Programming AGI runtime"),
    ("app.api.maximum_dynamic_agent_routes", "router",     "Maximum dynamic no-template programming AGI"),
    ("app.api.developer_experience_routes", "router",     "Developer Experience creative AGI tools"),
    ("app.api.platform_v4_routes", "router",     "Autonomous Dev Platform v4 phases 9-20"),
    ("app.api.agentic_visual_routes", "router",     "Agentic visual component AGI platform"),
    ("app.api.figma_agent_routes", "router",     "Figma design-to-code Agent"),
    ("app.api.unified_execution_routes", "router",     "Unified Dynamic Agent v12-v20"),
    ("app.api.autonomous_intelligence_v5_routes", "router",     "Autonomous Intelligence v21-v30"),
]

for module_path, attr_name, label in _OPTIONAL_ROUTERS:
    try:
        import importlib
        mod = importlib.import_module(module_path)
        r = getattr(mod, attr_name, None)
        if r is not None:
            app.include_router(r)
            print(f"✅ {label} endpoints loaded")
    except Exception as exc:
        print(f"⚠️  Could not load {label}: {exc}")
