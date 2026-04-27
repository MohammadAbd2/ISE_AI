from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

@dataclass(slots=True)
class ImportRepairPlan:
    missing_import: str
    source_file: str
    target_path: str
    reason: str

class AgentErrorResolver:
    IMPORT_RE = re.compile(r'Failed to resolve import "([^"]+)" from "([^"]+)"')

    def parse_vite_import_error(self, text: str) -> ImportRepairPlan | None:
        match = self.IMPORT_RE.search(text or "")
        if not match:
            return None
        missing, source = match.groups()
        source_path = Path(source)
        if "src" in source_path.parts:
            src_index = source_path.parts.index("src")
            source_dir = Path(*source_path.parts[src_index:]).parent
        else:
            source_dir = Path(source).parent
        target = (source_dir / missing).as_posix()
        if not Path(target).suffix:
            target += ".jsx"
        return ImportRepairPlan(missing, source, target, f"Create exact missing module imported by {source}: {missing}")

    def missing_import_steps(self, error_text: str) -> list[dict]:
        plan = self.parse_vite_import_error(error_text)
        if not plan:
            return []
        steps = [{"agent":"DebugAgent","action":"write_file","target":plan.target_path,"description":plan.reason,"content":self._component_for_path(plan.target_path)}]
        if plan.target_path.endswith("GlobalErrorBoundary.jsx"):
            steps.append({"agent":"DebugAgent","action":"write_file","target":"src/styles/global.css","description":"Ensure stylesheet imported by src/main.jsx exists","content":self._global_css()})
        steps.append({"agent":"VerifierAgent","action":"run_command","target":"npm run build","description":"Rebuild after exact import repair","command":"npm run build"})
        return steps

    def _component_for_path(self, target_path: str) -> str:
        if target_path.endswith("GlobalErrorBoundary.jsx"):
            return '''import React from "react";

export default class GlobalErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("GlobalErrorBoundary caught an error", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <main className="app-error-boundary" role="alert">
          <p className="app-error-boundary__eyebrow">Runtime protection</p>
          <h1>Something went wrong.</h1>
          <p>{this.state.error.message || "The app crashed while rendering."}</p>
          <button type="button" onClick={() => window.location.reload()}>Reload app</button>
        </main>
      );
    }
    return this.props.children;
  }
}
'''
        name = Path(target_path).stem
        return f'''import React from "react";

export default function {name[:1].upper() + name[1:]}() {{
  return <div>{name}</div>;
}}
'''

    def _global_css(self) -> str:
        return '''html { box-sizing: border-box; }
*, *::before, *::after { box-sizing: inherit; }
body { margin: 0; min-width: 320px; background: #08111f; color: #f8fafc; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
a { color: inherit; }
button { font: inherit; }
.app-error-boundary { min-height: 100vh; display: grid; place-items: center; padding: 2rem; text-align: center; background: radial-gradient(circle at top, rgba(248,113,113,.2), transparent 35%), #0f172a; }
.app-error-boundary__eyebrow { color: #fca5a5; font-weight: 900; letter-spacing: .16em; text-transform: uppercase; }
.app-error-boundary button { border: 0; border-radius: 999px; padding: .85rem 1.1rem; color: #450a0a; background: #fecaca; font-weight: 900; cursor: pointer; }
'''
