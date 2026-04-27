from __future__ import annotations
import json
import re
from app.services.downloadable_files import generate_downloadable_file


def _safe_label(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9 _.-]", "", str(value))[:80] or "Item"


def build_mermaid_diagram(kind: str, title: str, data) -> str:
    kind = (kind or "flowchart").lower()
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            data = {"steps": [x.strip() for x in data.splitlines() if x.strip()]}
    if not isinstance(data, dict):
        data = {"items": data}
    if kind == "sequence":
        lines = ["sequenceDiagram", f"    title {_safe_label(title)}"]
        actors = data.get("actors") or ["User", "Agent", "Tool"]
        steps = data.get("steps") or ["Plan", "Execute", "Verify"]
        for actor in actors:
            lines.append(f"    participant {_safe_label(actor).replace(' ', '')}")
        for i, step in enumerate(steps):
            src = _safe_label(actors[i % len(actors)]).replace(" ", "")
            dst = _safe_label(actors[(i + 1) % len(actors)]).replace(" ", "")
            lines.append(f"    {src}->>+{dst}: {_safe_label(step)}")
        return "\n".join(lines)
    lines = ["flowchart TD", f"    T[\"{_safe_label(title)}\"]"]
    steps = data.get("steps") or data.get("nodes") or data.get("items") or []
    if isinstance(steps, dict):
        steps = list(steps.values())
    if not steps:
        steps = ["Understand request", "Plan", "Execute", "Verify", "Return artifacts"]
    last = "T"
    for i, step in enumerate(steps[:30], 1):
        node = f"N{i}"
        label = _safe_label(step.get("label", step) if isinstance(step, dict) else step)
        lines.append(f"    {node}[\"{label}\"]")
        lines.append(f"    {last} --> {node}")
        last = node
    return "\n".join(lines)


async def generate_diagram_artifact(session_id: str, title: str, kind: str, data, export_format: str = "mmd") -> dict:
    mermaid = build_mermaid_diagram(kind, title, data)
    ext = ".html" if export_format == "html" else ".mmd"
    if ext == ".html":
        content = "<!doctype html><html><body><pre class='mermaid'>\n" + mermaid + "\n</pre><script type='module'>import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs'; mermaid.initialize({startOnLoad:true});</script></body></html>"
    else:
        content = mermaid
    file = await generate_downloadable_file(session_id, f"{title or 'diagram'}{ext}", content, ext, title or "Generated diagram")
    return {"diagram_type": "mermaid", "kind": kind, "title": title, "mermaid": mermaid, "artifact": file}
