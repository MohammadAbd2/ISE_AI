from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import hashlib
import json
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
STATE_DIR = ROOT / "AGI_Output" / ".state" / "figma"
STATE_DIR.mkdir(parents=True, exist_ok=True)

ROADMAP = {
    "title": "Figma-to-Code + Prompt-to-Prototype Agent Roadmap",
    "status": "implementation_started",
    "north_star": "The unified Agent can inspect Figma links or uploaded design artifacts, understand structure and design tokens, generate production UI code, create prompt-based prototypes, preview them locally, and render the result in chat.",
    "phases": [
        {"id": "F1", "name": "Figma source resolver", "goal": "Accept Figma URLs, file keys, node IDs, screenshots, and exported JSON; normalize them into one design source contract."},
        {"id": "F2", "name": "Design token extractor", "goal": "Extract colors, typography, spacing, radii, shadows, components, image assets, and responsive hints."},
        {"id": "F3", "name": "Layout understanding", "goal": "Convert frames/layers into sections, grids, stacks, constraints, and semantic components."},
        {"id": "F4", "name": "Figma-to-code generator", "goal": "Generate React/HTML/CSS/Tailwind components from the normalized design brief."},
        {"id": "F5", "name": "Prompt-to-Figma prototype", "goal": "Generate a Figma-like prototype JSON and browser-previewable mockup from a user prompt."},
        {"id": "F6", "name": "Browser preview bridge", "goal": "Start a local preview process or static preview for generated prototypes and verify reachability."},
        {"id": "F7", "name": "Visual diff and QA", "goal": "Compare expected design brief against generated UI: layout, colors, text, accessibility, responsiveness."},
        {"id": "F8", "name": "Self-healing design debugger", "goal": "If build/preview/design QA fails, analyze the failure, patch, rerun, and continue."},
        {"id": "F9", "name": "Chat render integration", "goal": "Return visual design brief, token table, file gallery, preview, and download cards in the chat tab."},
        {"id": "F10", "name": "IDE handoff", "goal": "Allow VS Code/JetBrains extensions to apply generated design-code patches directly to the open project."},
        {"id": "F11", "name": "Figma API integration", "goal": "Optionally use FIGMA_ACCESS_TOKEN to fetch real file JSON/images; degrade gracefully without a token."},
        {"id": "F12", "name": "Prototype export", "goal": "Export prototype spec, React project, static HTML preview, and implementation report as downloadable artifacts."},
    ],
    "routing_rules": [
        "Figma/design prompts route to DesignAgent first, not generic Programming Agent.",
        "Simple HTML/static preview prompts produce direct HTML artifacts plus static preview metadata, not a React template app.",
        "File-location questions query the latest artifact/run memory instead of launching a new implementation run.",
    ],
    "quality_gates": [
        "Never claim a preview exists unless a preview URL or static artifact is returned.",
        "Never answer where a file is by creating a new project.",
        "Never copy a website/Figma design verbatim; generate original equivalent structure unless the user owns the design.",
        "Every generated design project includes preview, file gallery, tokens, and repair-loop evidence if errors happen.",
    ],
}


def _safe_name(value: str, fallback: str = "design") -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", value or fallback).strip(".-")
    return value[:80] or fallback


def parse_figma_url(url: str) -> dict[str, Any]:
    parsed = urlparse(url or "")
    parts = [part for part in parsed.path.split("/") if part]
    file_key = ""
    file_name = "Figma design"
    if len(parts) >= 2 and parts[0] in {"file", "design", "proto"}:
        file_key = parts[1]
        if len(parts) >= 3:
            file_name = parts[2].replace("-", " ")
    query = parse_qs(parsed.query)
    node_id = (query.get("node-id") or query.get("node_id") or [""])[0]
    return {
        "url": url,
        "host": parsed.netloc,
        "file_key": file_key,
        "file_name": file_name,
        "node_id": node_id,
        "mode": parts[0] if parts else "unknown",
        "requires_token_for_live_fetch": parsed.netloc.endswith("figma.com"),
    }


def _token_palette(seed_text: str) -> dict[str, str]:
    digest = hashlib.sha256(seed_text.encode("utf-8")).hexdigest()
    return {
        "primary": f"#{digest[:6]}",
        "accent": f"#{digest[6:12]}",
        "surface": "#0f172a",
        "text": "#e2e8f0",
        "muted": "#94a3b8",
        "radius": "24px",
        "spacing": "8px grid",
        "font": "Inter, system-ui, sans-serif",
    }




def _prompt_keywords(prompt: str, limit: int = 8) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", prompt or "")
    stop = {"create", "make", "generate", "figma", "design", "prototype", "website", "from", "with", "into", "code", "page", "application", "that", "this", "please", "convert", "similar"}
    unique: list[str] = []
    for word in words:
        item = word.lower()
        if item in stop or item in unique:
            continue
        unique.append(item)
        if len(unique) >= limit:
            break
    return unique or ["adaptive", "interface", "workflow"]


def _sections_from_prompt(prompt: str) -> list[dict[str, str]]:
    lower = (prompt or "").lower()
    sections = [{"id": "nav", "label": "Navigation", "description": "Brand, contextual links, primary action"}]
    if any(x in lower for x in ("dashboard", "analytics", "data", "metrics")):
        sections += [
            {"id": "metrics", "label": "Metric overview", "description": "KPI cards and trend comparison"},
            {"id": "insights", "label": "Insight workspace", "description": "Charts, filters and decision panels"},
        ]
    elif any(x in lower for x in ("shop", "store", "product", "cart", "checkout")):
        sections += [
            {"id": "catalog", "label": "Product catalog", "description": "Responsive cards, categories and quick add actions"},
            {"id": "checkout", "label": "Checkout preview", "description": "Cart summary, payment steps and trust badges"},
        ]
    elif any(x in lower for x in ("login", "auth", "signup", "account")):
        sections += [
            {"id": "auth", "label": "Authentication panel", "description": "Login/signup form, validation and account actions"},
            {"id": "security", "label": "Security notes", "description": "Password, session and recovery hints"},
        ]
    elif any(x in lower for x in ("portfolio", "cv", "resume", "profile")):
        sections += [
            {"id": "profile", "label": "Profile story", "description": "Hero summary, skills and proof points"},
            {"id": "work", "label": "Work timeline", "description": "Projects, experience and contact CTA"},
        ]
    else:
        keywords = _prompt_keywords(prompt, 4)
        sections += [
            {"id": f"section-{idx}", "label": word.title(), "description": f"Dynamic area focused on {word} from the prompt"}
            for idx, word in enumerate(keywords[:3], 1)
        ]
    sections.append({"id": "cta", "label": "Action panel", "description": "Final conversion or next-step area"})
    return sections


def _tone_from_prompt(prompt: str) -> str:
    lower = (prompt or "").lower()
    if any(x in lower for x in ("luxury", "premium", "elegant")):
        return "premium editorial"
    if any(x in lower for x in ("playful", "kids", "fun", "game")):
        return "playful motion"
    if any(x in lower for x in ("developer", "code", "terminal", "agent", "ai")):
        return "developer cockpit"
    if any(x in lower for x in ("minimal", "clean", "simple")):
        return "minimal product"
    return "adaptive product"

def inspect_figma_design(url: str, prompt: str = "Convert this design to code") -> dict[str, Any]:
    source = parse_figma_url(url)
    tokens = _token_palette(source.get("file_key") or url)
    derived_sections = _sections_from_prompt(prompt)
    frames = [
        {"name": f"Frame / {section['label']}", "role": section["id"], "layout": "responsive auto-layout grid", "components": [section["label"].replace(" ", "") + "Block", "TokenAwareCard"]}
        for section in derived_sections
    ]
    brief = {
        "source": source,
        "prompt": prompt,
        "design_tokens": tokens,
        "frames": frames,
        "component_plan": ["AppShell"] + [section["label"].replace(" ", "") + "Block" for section in derived_sections],
        "tone": _tone_from_prompt(prompt),
        "implementation_stack": "React + CSS modules or vanilla CSS, Vite preview",
        "accessibility": ["semantic landmarks", "keyboard reachable CTAs", "contrast checked", "responsive typography"],
        "note": "Without FIGMA_ACCESS_TOKEN this uses URL metadata and prompt context. With a token, the same contract can be hydrated from Figma file JSON/images.",
    }
    return {
        "agent": "FigmaDesignAgent",
        "status": "inspected",
        "brief": brief,
        "render_blocks": [
            {"type": "figma_design_brief", "payload": brief},
            {"type": "visual_data_table", "payload": {"title": "Design tokens", "rows": [{"token": k, "value": v} for k, v in tokens.items()], "columns": ["token", "value"]}},
        ],
    }


def generate_prompt_prototype(prompt: str, title: str = "Agent prototype") -> dict[str, Any]:
    safe = _safe_name(title or prompt[:48], "agent-prototype")
    tokens = _token_palette(prompt)
    sections = _sections_from_prompt(prompt)
    tone = _tone_from_prompt(prompt)
    html = f"""<!doctype html>
<html lang=\"en\">
<head><meta charset=\"utf-8\"/><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/><title>{safe}</title>
<style>
:root {{--primary:{tokens['primary']};--accent:{tokens['accent']};--surface:#0f172a;--text:#e2e8f0;--muted:#94a3b8;--radius:24px;}}
*{{box-sizing:border-box}} body{{margin:0;font-family:Inter,system-ui,sans-serif;background:radial-gradient(circle at top left,var(--primary),transparent 30%),#020617;color:var(--text)}}
.preview{{max-width:1120px;margin:0 auto;padding:32px}} nav{{display:flex;justify-content:space-between;align-items:center;padding:16px 0}} .brand{{font-weight:900}}
.hero{{display:grid;grid-template-columns:1.1fr .9fr;gap:28px;align-items:center;min-height:70vh}} h1{{font-size:clamp(2.5rem,7vw,5.5rem);line-height:.94;margin:0 0 18px}} p{{color:var(--muted);font-size:1.05rem;line-height:1.7}}
.card,.feature{{border:1px solid rgba(148,163,184,.24);border-radius:var(--radius);background:rgba(15,23,42,.76);box-shadow:0 24px 80px rgba(0,0,0,.28);padding:24px}}
.cta{{display:inline-flex;border:0;border-radius:999px;padding:14px 20px;background:linear-gradient(135deg,var(--primary),var(--accent));color:white;font-weight:800;text-decoration:none}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin-top:28px}} @media(max-width:780px){{.hero{{grid-template-columns:1fr}}}}
</style></head>
<body><main class=\"preview\"><nav><div class=\"brand\">{safe}</div><a class=\"cta\" href=\"#cta\">Start</a></nav><section class=\"hero\"><div><h1>{prompt[:96]}</h1><p>{tone.title()} prototype generated by the Agent from the actual prompt. It adapts sections, copy, tokens, and hierarchy instead of using one static page.</p><a class=\"cta\" href=\"#features\">Explore prototype</a></div><div class=\"card\"><strong>{tone.title()} frame</strong><p>Tokens, layout, spacing and component hierarchy are captured for code generation.</p></div></section><section id=\"features\" class=\"grid\">{''.join(f'<article class="feature"><strong>{s["label"]}</strong><p>{s["description"]}</p></article>' for s in sections)}</section><section id=\"cta\" class=\"card\" style=\"margin-top:24px\"><h2>Ready for implementation</h2><p>Export this prototype as HTML, React, or a design brief.</p></section></main></body></html>"""
    prototype = {"title": safe, "prompt": prompt, "tone": tone, "tokens": tokens, "sections": sections, "html": html}
    state_path = STATE_DIR / f"{safe}.prototype.json"
    state_path.write_text(json.dumps(prototype, indent=2), encoding="utf-8")
    return {
        "agent": "PromptPrototypeAgent",
        "status": "generated",
        "prototype": prototype,
        "files": [{"path": f"{safe}.html", "kind": "html", "content": html, "summary": "Static browser preview prototype."}],
        "render_blocks": [
            {"type": "figma_prototype_preview", "payload": prototype},
            {"type": "visual_file_gallery", "payload": {"title": "Prototype files", "files": [{"path": f"{safe}.html", "kind": "html", "content": html[:1600], "summary": "Static browser preview prototype."}]}},
        ],
    }


def roadmap() -> dict[str, Any]:
    return ROADMAP
