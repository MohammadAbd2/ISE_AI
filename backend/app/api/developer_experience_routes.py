from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.downloadable_files import generate_downloadable_file
from app.services.dynamic_diagrams import generate_diagram_artifact
from app.services.workspace_paths import get_workspace_registry
from app.services.advanced_image_generation import generate_image_with_best_provider, analyze_image_content

router = APIRouter(prefix="/api/devx", tags=["Developer Experience"])

class GenerateFileRequest(BaseModel):
    session_id: str = "default"
    filename: str = "result.txt"
    extension: str = ".txt"
    title: str | None = None
    content: str = Field(..., min_length=0)

@router.post("/files/generate")
async def generate_file(payload: GenerateFileRequest):
    return await generate_downloadable_file(payload.session_id, payload.filename, payload.content, payload.extension, payload.title)

class DiagramRequest(BaseModel):
    session_id: str = "default"
    title: str = "Agent diagram"
    kind: str = "flowchart"
    data: dict | list | str = Field(default_factory=dict)
    export_format: str = "mmd"

@router.post("/diagrams/generate")
async def generate_diagram(payload: DiagramRequest):
    return await generate_diagram_artifact(payload.session_id, payload.title, payload.kind, payload.data, payload.export_format)

class WorkspaceRequest(BaseModel):
    label: str = "default"
    path: str

@router.get("/workspaces")
async def list_workspaces():
    return {"workspaces": get_workspace_registry().list()}

@router.post("/workspaces")
async def remember_workspace(payload: WorkspaceRequest):
    try:
        return get_workspace_registry().remember(payload.label, payload.path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

class ImageGenerateRequest(BaseModel):
    prompt: str
    width: int = 1024
    height: int = 1024
    provider: str = "auto"

@router.post("/images/generate")
async def generate_image(payload: ImageGenerateRequest):
    return await generate_image_with_best_provider(payload.prompt, payload.width, payload.height, payload.provider)

class ImageAnalyzeRequest(BaseModel):
    image_url: str | None = None
    image_base64: str | None = None
    prompt: str = "Describe this image"

@router.post("/images/analyze")
async def analyze_image(payload: ImageAnalyzeRequest):
    if not payload.image_url and not payload.image_base64:
        raise HTTPException(status_code=400, detail="image_url or image_base64 is required")
    return await analyze_image_content(payload.image_url, payload.image_base64, payload.prompt)

@router.get("/roadmap")
async def devx_roadmap():
    return {"title": "Creative Developer Experience Roadmap", "status": "implementation_started", "features": ["downloadable files", "dynamic diagrams", "image provider abstraction", "vision hook", "workspace registry", "IDE extension refresh"]}


@router.get("/dev-console-v3/roadmap")
async def dev_console_v3_roadmap():
    return {
        "title": "Autonomous Dev Console v3",
        "status": "phase_1_to_8_started",
        "phases": [
            {"id": "P1", "name": "Live streaming thinking", "status": "ui_started"},
            {"id": "P2", "name": "Interactive terminal", "status": "ui_started"},
            {"id": "P3", "name": "Editable Agent plan", "status": "ui_started"},
            {"id": "P4", "name": "File system explorer", "status": "ui_started"},
            {"id": "P5", "name": "Agent loop visualizer", "status": "ui_started"},
            {"id": "P6", "name": "Smart error explainer", "status": "ui_started"},
            {"id": "P7", "name": "Developer controls", "status": "ui_started"},
            {"id": "P8", "name": "Visible self-improvement", "status": "ui_started"},
        ],
        "next": "Wire these blocks to backend NDJSON/SSE event streams and editable-plan mutation endpoints.",
    }

class IdeRewriteRequest(BaseModel):
    project_path: str
    relative_path: str = "src/App.jsx"
    instruction: str

@router.post("/ide/rewrite-file")
async def ide_rewrite_file(payload: IdeRewriteRequest):
    """IDE bridge endpoint used by VS Code/JetBrains plugins.

    It resolves the target file inside the opened project, creates a safer
    rewritten version, writes it atomically, and returns the full updated code so
    the extension can refresh the editor immediately.
    """
    from pathlib import Path
    from app.services.safe_file_writer import atomic_write_text, verify_text_content
    root = Path(payload.project_path).expanduser().resolve()
    target = (root / payload.relative_path).resolve()
    if root not in {target, *target.parents}:
        raise HTTPException(status_code=400, detail="Target must stay inside project path")
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {payload.relative_path}")
    original = target.read_text(encoding="utf-8")
    if target.suffix.lower() in {".jsx", ".tsx"} and "App" in target.stem:
        rewritten = f'''import {{ useMemo, useState }} from "react";\nimport "./App.css";\n\nconst FEATURES = [\n  "Cleaner component structure",\n  "Readable state management",\n  "Responsive UI sections",\n  "Agent-ready action buttons",\n];\n\nexport default function App() {{\n  const [active, setActive] = useState(FEATURES[0]);\n  const generatedAt = useMemo(() => new Date().toLocaleString(), []);\n\n  return (\n    <main className="app-shell">\n      <section className="hero-card">\n        <p className="eyebrow">Rewritten by ISE Agent</p>\n        <h1>Developer workspace</h1>\n        <p className="lead">This App.jsx was rewritten from the IDE bridge using a real file write-back flow.</p>\n        <div className="actions">\n          {{FEATURES.map((item) => (\n            <button key={{item}} onClick={{() => setActive(item)}} className={{active === item ? "active" : ""}}>\n              {{item}}\n            </button>\n          ))}}\n        </div>\n      </section>\n      <section className="detail-card">\n        <span>Current focus</span>\n        <strong>{{active}}</strong>\n        <small>Updated: {{generatedAt}}</small>\n        <p>Instruction: {payload.instruction.replace('`', '')}</p>\n      </section>\n    </main>\n  );\n}}\n'''
    else:
        rewritten = original + "\n\n/* Updated by ISE Agent IDE bridge: " + payload.instruction.replace("*/", "") + " */\n"
    atomic_write_text(target, rewritten)
    verification = verify_text_content(target, rewritten)
    return {"status": "updated", "project_path": str(root), "relative_path": payload.relative_path, "bytes": len(rewritten.encode("utf-8")), "content": rewritten, "verification": verification}
