from pathlib import Path
import py_compile

ROOT = Path(__file__).resolve().parents[1]
required = [
    "backend/app/services/maximum_dynamic_agent.py",
    "backend/app/api/maximum_dynamic_agent_routes.py",
    "frontend/src/components/MaximumDynamicAgentPanel.jsx",
    "frontend/src/styles/maximum-dynamic-agent.css",
    "docs/NEXT_MAXIMUM_DYNAMIC_AGENT_ROADMAP.md",
]
missing = [path for path in required if not (ROOT / path).exists()]
if missing:
    raise SystemExit({"missing": missing})
py_compile.compile(str(ROOT / "backend/app/services/maximum_dynamic_agent.py"), doraise=True)
py_compile.compile(str(ROOT / "backend/app/api/maximum_dynamic_agent_routes.py"), doraise=True)
print("maximum dynamic agent verification passed")
