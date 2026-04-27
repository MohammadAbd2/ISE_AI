"""Production autonomous loop engine.

This engine is intentionally stricter than the older planning fallback:
- PlannerAgent may only produce structured steps.
- BuilderAgent may only mutate files through ProductionToolRuntime.
- VerifierAgent must validate writes and builds.
- DebugAgent can repair failed build steps and retry.
- ExportAgent never hallucinates links; export is handled by artifact service.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable

import httpx

from app.core.config import settings
from app.services.production_agent_runtime import ProductionToolRuntime
from app.services.agent_memory import get_agent_memory_store
from app.services.agent_protocol import AgentSharedContext, AgentTeamProtocol
from app.services.agent_error_resolver import AgentErrorResolver

ProgressCallback = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass(slots=True)
class AutonomousLoopResult:
    status: str
    summary: str
    changed_files: list[dict[str, Any]]
    steps: list[dict[str, Any]]
    verification: list[dict[str, Any]] = field(default_factory=list)
    elapsed_seconds: int = 0


STOP_WORDS = {
    "create", "build", "make", "implement", "generate", "using", "with", "react", "node",
    "roadmap", "road", "map", "plan", "project", "website", "landing", "page", "download",
    "downloadable", "zip", "file", "files", "give", "me", "then", "and", "for", "the", "a",
    "an", "to", "in", "sandbox", "agents", "agent", "fix", "issue", "if", "appear",
    "achive", "achieve", "task", "end", "nice", "some", "use", "download", "final",
}


def _title_case_words(text: str) -> str:
    words = [w for w in re.findall(r"[a-zA-Z0-9]+", text) if w]
    return " ".join(word.capitalize() for word in words[:6]) or "Generated Project"


def _safe_slug(text: str, fallback: str = "generated-project") -> str:
    slug = "-".join(re.findall(r"[a-z0-9]+", text.lower()))[:80].strip("-")
    return slug or fallback


def _extract_subject(task: str) -> str:
    lower = task.lower()
    # Prefer explicit "for ..." phrases but trim operation words after the useful noun phrase.
    match = re.search(r"\bfor\s+(?:a|an|the)?\s*([^,.]+?)(?:\s+using\b|\s+with\b|\s+create\b|\s+build\b|\s+then\b|\s+and\s+give\b|$)", lower)
    candidate = match.group(1) if match else lower
    tokens = [t for t in re.findall(r"[a-z0-9]+", candidate) if t not in STOP_WORDS]
    if not tokens:
        # Fall back to meaningful words from the full task.
        tokens = [t for t in re.findall(r"[a-z0-9]+", lower) if t not in STOP_WORDS]
    return _title_case_words(" ".join(tokens[:5]))


def _requested_stacks(task: str) -> set[str]:
    lower = task.lower()
    stacks: set[str] = set()
    if any(term in lower for term in ("react", "vite", "frontend", "login page", "website")):
        stacks.add("react")
    if any(term in lower for term in ("c#", "csharp", ".net", "asp.net", "dotnet")):
        stacks.add("dotnet")
    if any(term in lower for term in ("mysql", "mariadb", "database", "db")):
        stacks.add("mysql")
    if any(term in lower for term in ("login", "auth", "authentication", "jwt")):
        stacks.add("auth")
    return stacks


def _requires_full_stack(task: str) -> bool:
    stacks = _requested_stacks(task)
    lower = task.lower()
    explicit_full_stack = "full stack" in lower or "fullstack" in lower
    domain_app = any(term in lower for term in ("restaurant", "resturant", "reservation", "booking", "dashboard"))
    return (("dotnet" in stacks or "mysql" in stacks or "auth" in stacks) and "react" in stacks) or (explicit_full_stack and ("react" in stacks or domain_app))


def _infer_app_kind(task: str) -> str:
    lower = task.lower()
    if _requires_full_stack(task):
        return "full_stack"
    if any(term in lower for term in ("cms", "content management", "admin panel", "dashboard")):
        return "cms"
    if any(term in lower for term in ("landing page", "website", "home page", "homepage")):
        return "landing_page"
    if any(term in lower for term in ("component", "jsx", "tsx")):
        return "component"
    return "application"


def _component_name_from_task(task: str) -> tuple[str, str, str]:
    lower = task.lower()
    explicit = re.search(r"([A-Za-z0-9_\-]+)\.(jsx|tsx|js|ts)", task)
    if explicit:
        file_name = explicit.group(1) + "." + explicit.group(2)
    elif "hello world" in lower or "hellow world" in lower:
        file_name = "HelloWorld.jsx"
    else:
        before_component = re.search(r"(?:create|build|make|implement)?\s*(?:a|an|the)?\s*([a-zA-Z0-9_\-\s]{2,48}?)\s+component\b", task, re.I)
        subject = before_component.group(1) if before_component else _extract_subject(task)
        tokens = [t for t in re.findall(r"[A-Za-z0-9]+", subject) if t.lower() not in STOP_WORDS]
        stem = "".join(t.capitalize() for t in tokens[:3]) or "Component"
        if not stem.lower().endswith("component") and "component" in lower:
            stem = f"{stem}Component"
        file_name = f"{stem}.jsx"
    stem = Path(file_name).stem
    component_name = stem if re.match(r"^[A-Z][A-Za-z0-9]*$", stem) else "".join(part.capitalize() for part in re.split(r"[^A-Za-z0-9]", stem) if part) or "Component"
    style_ext = "scss" if any(term in lower for term in ("scss", "sass")) else "css"
    style_match = re.search(r"([A-Za-z0-9_\-]+\.(?:css|scss|sass))", task, re.I)
    style_name = style_match.group(1) if style_match else f"{stem}.{style_ext}"
    return file_name, component_name, style_name


class AutonomousLoopEngine:
    """Drop-in autonomous loop for production-style project generation."""

    def __init__(self, workspace: Path, session_id: str | None = None, progress_callback: ProgressCallback | None = None) -> None:
        self.workspace = workspace.resolve()
        self.session_id = session_id
        self.progress_callback = progress_callback
        self.runtime = ProductionToolRuntime(workspace=self.workspace, session_id=session_id, progress_callback=progress_callback)
        self.memory = get_agent_memory_store()
        self.shared_context: AgentSharedContext | None = None
        self.team: AgentTeamProtocol | None = None
        self.started = time.monotonic()
        self.changed_paths: list[str] = []
        self.steps: list[dict[str, Any]] = []
        self.verification: list[dict[str, Any]] = []
        self.error_resolver = AgentErrorResolver()

    async def run(self, task: str, *, workspace_mode: str = "focused") -> AutonomousLoopResult:
        self.shared_context = AgentSharedContext(task=task, run_id=self.session_id)
        self.team = AgentTeamProtocol(self.shared_context)
        planning_context = self.memory.planning_context(task, limit=4)
        similar = self.memory.search(task, limit=3)
        lessons = self.memory.search_lessons(task, limit=4)
        self.shared_context.send("PlannerAgent", "Memory", "decision", f"Retrieved {len(similar)} similar task memories and {len(lessons)} lessons before planning.", hits=[asdict(hit) for hit in similar], lessons=[asdict(item) for item in lessons])
        await self.runtime.emit("PlannerAgent", "memory", "completed", f"Retrieved {len(similar)} memories + {len(lessons)} lessons", estimated_seconds=60)
        await self.runtime.emit("PlannerAgent", "analyze", "running", "Analyzing request and deriving architecture", estimated_seconds=180)
        plan = await self._build_plan(task, workspace_mode=workspace_mode, similar_memories=similar)
        self.shared_context.send("PlannerAgent", "BuilderAgent", "decision", f"Created {len(plan)} executable steps.", plan=plan)
        if self.team:
            self.team.planner_to_builder(f"Created {len(plan)} executable steps from request-specific architecture.", plan=plan)
        if not any(step.get("action") == "export_zip" for step in plan):
            plan.append(self._export_step(task, workspace_mode=workspace_mode))
        await self.runtime.emit("PlannerAgent", "plan", "completed", f"Created {len(plan)} executable steps", estimated_seconds=max(30, len(plan) * 20), output=json.dumps([{k: v for k, v in item.items() if k != "content"} for item in plan], indent=2)[:900])

        status = "completed"
        for index, step in enumerate(plan, start=1):
            step_result = {"step_number": index, "agent": step.get("agent", "BuilderAgent"), "description": step["description"], "target": step.get("target", ""), "status": "running", "output": "", "error": ""}
            self.steps.append(step_result)
            try:
                await self._execute_step(step, step_result)
                step_result["status"] = "completed"
            except Exception as exc:
                step_result["status"] = "failed"
                step_result["error"] = str(exc)[:1000]
                await self.runtime.emit("DebugAgent", "repair", "running", f"Repairing failed step {index}: {exc}", estimated_seconds=180, error=str(exc)[:700])
                repaired = await self._repair_and_retry(step, step_result, str(exc))
                if repaired:
                    step_result["status"] = "completed"
                    if self.shared_context:
                        self.shared_context.send("DebugAgent", "VerifierAgent", "decision", f"Repaired step {index} after failure.", step=index)
                else:
                    status = "failed"
                    if self.shared_context:
                        self.shared_context.send("DebugAgent", "PlannerAgent", "error", str(exc), step=index)
                    await self.runtime.emit("DebugAgent", "repair", "failed", f"Could not repair step {index}", estimated_seconds=180, error=str(exc)[:700])
                    break

        elapsed = max(0, int(time.monotonic() - self.started))
        changed = [self._file_payload(path) for path in dict.fromkeys(self.changed_paths) if (self.workspace / path).is_file()]
        summary = f"Autonomous loop finished with {sum(1 for s in self.steps if s['status'] == 'completed')}/{len(self.steps)} steps completed."
        failures = [s.get("error", "") for s in self.steps if s.get("error")]
        files = [item["path"] for item in changed if item.get("path")]
        self.memory.record_run(task=task, success=status == "completed", summary=summary, files=files, failures=failures, fixes=[s.get("output", "") for s in self.steps if s.get("status") == "completed"], metadata={"verification": self.verification})
        if self.progress_callback and self.shared_context:
            await self.progress_callback({"type": "agent_timeline", "payload": self.shared_context.to_render_payload() | {"title": "Agent collaboration", "status": status, "timing": {"elapsed_seconds": max(1, elapsed), "estimated_seconds": max(1, elapsed)}}})
        return AutonomousLoopResult(status=status, summary=summary, changed_files=changed, steps=self.steps, verification=self.verification, elapsed_seconds=elapsed)

    async def _build_plan(self, task: str, *, workspace_mode: str, similar_memories: list[Any] | None = None) -> list[dict[str, Any]]:
        import_repair = self.error_resolver.missing_import_steps(task)
        if import_repair:
            return import_repair
        # Complex stack requests bypass memories/templates: they need every requested layer.
        if _requires_full_stack(task):
            return self._full_stack_login_plan(task, workspace_mode=workspace_mode)
        # Try an LLM architecture first. If unavailable or invalid, use deterministic request-derived planning.
        llm_plan = await self._try_llm_plan(task, similar_memories=similar_memories or [])
        if llm_plan:
            return llm_plan
        return self._fallback_plan(task, workspace_mode=workspace_mode)

    async def _try_llm_plan(self, task: str, similar_memories: list[Any] | None = None) -> list[dict[str, Any]]:
        try:
            model = getattr(settings, "ollama_model", "auto")
            if model == "auto":
                from app.services.model_manager import get_model_manager
                model = get_model_manager().select_model("coding")
            prompt = (
                "Return ONLY compact JSON for an autonomous coding plan. No markdown. "
                "Schema: {\"steps\":[{\"agent\":\"BuilderAgent|VerifierAgent\",\"action\":\"write_file|run_command\",\"path\":\"relative path or empty\",\"description\":\"...\",\"content\":\"file content for write_file only\",\"command\":\"command for run_command only\"}]}. "
                "Create production-quality, request-specific files for every requested stack. Do not use placeholder text, fake links, or mock results. If the task asks for React + C#/.NET + MySQL, a React-only output is invalid: generate frontend, backend, database schema, setup docs, and verification commands. "
                "If the task is a Vite import error, create the exact missing imported file path; never create src/components/main.jsx for src/main.jsx errors. "
                "For CV/resume landing pages, produce real header/body/footer sections: identity, headline, skills, experience, selected work, contact, and footer. "
                "Use these prior run lessons when relevant, but do not copy stale outputs: "
                f"{json.dumps([asdict(hit) for hit in (similar_memories or [])], ensure_ascii=False)[:1200]}\n"
                f"Task: {task}"
            )
            async with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=120.0) as client:
                resp = await client.post("/api/generate", json={"model": model, "prompt": prompt, "stream": False})
            resp.raise_for_status()
            text = resp.json().get("response", "")
            data = self._parse_json(text)
            steps = data.get("steps") if isinstance(data, dict) else None
            if not isinstance(steps, list) or not steps:
                return []
            normalized = []
            for item in steps[:12]:
                if not isinstance(item, dict):
                    continue
                action = item.get("action")
                if action == "write_file" and item.get("path") and item.get("content"):
                    normalized.append({"agent": item.get("agent") or "BuilderAgent", "action": "write_file", "target": item["path"], "description": item.get("description") or f"Write {item['path']}", "content": item["content"]})
                elif action == "run_command" and item.get("command"):
                    normalized.append({"agent": item.get("agent") or "VerifierAgent", "action": "run_command", "target": item["command"], "description": item.get("description") or item["command"], "command": item["command"]})
            return normalized
        except Exception:
            return []

    def _parse_json(self, text: str) -> Any:
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text).strip()
            text = re.sub(r"```$", "", text).strip()
        match = re.search(r"\{.*\}", text, re.S)
        return json.loads(match.group(0) if match else text)

    def _fallback_plan(self, task: str, *, workspace_mode: str) -> list[dict[str, Any]]:
        import_repair = self.error_resolver.missing_import_steps(task)
        if import_repair:
            return import_repair
        kind = _infer_app_kind(task)
        if kind == "full_stack":
            return self._full_stack_login_plan(task, workspace_mode=workspace_mode)
        if kind == "component":
            jsx_name, component_name, css_name = _component_name_from_task(task)
            css_class = re.sub(r"[^a-z0-9-]", "-", Path(css_name).stem.lower()).strip("-") or "generated-component"
            return [
                {"agent": "BuilderAgent", "action": "write_file", "target": f"frontend/src/components/{jsx_name}", "description": f"Create React component {component_name}", "content": self._component_jsx(component_name, css_name, css_class, task)},
                {"agent": "BuilderAgent", "action": "write_file", "target": f"frontend/src/components/{css_name}", "description": f"Create stylesheet {css_name}", "content": self._component_css(css_class)},
            ]
        # For every non-component app, route through the dynamic contract
        # runtime. This removes the old static CV/landing shell and ensures
        # commerce, restaurant, auth, backend, and database requests produce the
        # correct stack-specific file graph.
        from app.services.dynamic_agent_runtime import get_dynamic_agent_runtime
        runtime = get_dynamic_agent_runtime()
        files = runtime.build_artifact_graph(task)
        plan = []
        for path, content in files.items():
            plan.append({"agent": "BuilderAgent", "action": "write_file", "target": path, "description": f"Write dynamic artifact {path}", "content": content})
        plan.append({"agent": "VerifierAgent", "action": "run_command", "target": "python3 scripts/verify_artifact.py", "description": "Verify dynamic artifact gates", "command": "python3 scripts/verify_artifact.py"})
        if "frontend/package.json" in files:
            plan.append({"agent": "VerifierAgent", "action": "run_command", "target": "cd frontend && npm run build", "description": "Build React frontend", "command": "cd frontend && npm run build"})
        return plan

    def _export_step(self, task: str, *, workspace_mode: str) -> dict[str, Any]:
        subject = _extract_subject(task)
        slug = _safe_slug(subject or task, fallback="generated-output")
        kind = _infer_app_kind(task)
        suffix = "component" if kind == "component" else "project"
        return {
            "agent": "ExportAgent",
            "action": "export_zip",
            "target": "verified-artifact.zip",
            "task": task,
            "title": f"{subject} {suffix.title()} ZIP",
            "filename": f"{slug}-{suffix}.zip",
            "description": "Create verified downloadable ZIP from generated sandbox files",
        }

    async def _execute_step(self, step: dict[str, Any], step_result: dict[str, Any]) -> None:
        action = step.get("action")
        if action == "write_file":
            target = step["target"]
            result = await self.runtime.write_file(target, step.get("content", ""))
            self.changed_paths.append(target)
            if self.shared_context:
                self.shared_context.send("BuilderAgent", "VerifierAgent", "file", f"Wrote {target}", path=target, bytes=result["bytes"])
            step_result["output"] = f"Wrote and verified {target} ({result['bytes']} bytes)."
        elif action == "run_command":
            command = step.get("command") or step.get("target")
            result = await self.runtime.run_command(command, timeout=240)
            self.verification.append(result)
            if self.shared_context:
                self.shared_context.send("VerifierAgent", "PlannerAgent", "decision", f"Verified command: {command}", return_code=result.get("return_code"))
            step_result["output"] = (result.get("stdout") or result.get("stderr") or "Command completed")[:900]
        elif action == "playwright_check":
            result = await self._run_playwright_smoke_check()
            self.verification.append(result)
            step_result["output"] = result.get("summary", "Playwright check processed")
        elif action == "export_zip":
            paths = [path for path in dict.fromkeys(self.changed_paths) if (self.workspace / path).is_file()]
            if not paths:
                raise RuntimeError("Export refused because no generated files were found")
            task_text = str(step.get("task") or "")
            inferred_kind = _infer_app_kind(task_text)
            if inferred_kind == "component":
                package_root = "generated-files"
            elif inferred_kind == "full_stack":
                package_root = "generated-fullstack-project"
            else:
                package_root = "generated-react-project"
            await self._validate_requirements_before_export(task_text, paths)
            result = await self.runtime.export_zip(paths, title=step.get("title") or "Generated artifact", filename=step.get("filename") or "generated-output.zip", package_root=package_root, task=task_text)
            artifact = result.get("artifact") or {}
            if self.shared_context and self.team:
                self.team.exporter_to_user("Created verified downloadable ZIP artifact.", artifact_id=artifact.get("id"), file_count=result.get("file_count"), paths=paths)
            step_result["output"] = f"Created ZIP artifact with {result.get('file_count')} files."
            step_result["artifact"] = artifact
        else:
            raise ValueError(f"Unsupported agent action: {action}")

    async def _repair_and_retry(self, step: dict[str, Any], step_result: dict[str, Any], error: str) -> bool:
        # Deterministic repair for the common frontend cwd/package case.
        if step.get("action") == "run_command" and "package.json" in error.lower() and "cd frontend" not in str(step.get("command", "")):
            step["command"] = f"cd frontend && {step.get('command') or step.get('target')}"
            step["target"] = step["command"]
            try:
                await self._execute_step(step, step_result)
                return True
            except Exception as retry_error:
                step_result["error"] = str(retry_error)[:1000]
                return False
        if self.team:
            self.team.verifier_to_debugger(error, step=step)
        return False

    async def _run_playwright_smoke_check(self) -> dict[str, Any]:
        frontend = self.workspace / "frontend"
        if not (frontend / "node_modules" / "@playwright" / "test").exists():
            await self.runtime.emit("VerifierAgent", "playwright", "skipped", "Playwright is not installed; npm build already verified static output", estimated_seconds=180)
            return {"command": "playwright smoke", "return_code": 0, "summary": "Skipped: @playwright/test is not installed in this workspace."}
        test_dir = frontend / "tests"
        test_dir.mkdir(parents=True, exist_ok=True)
        smoke = test_dir / "ise-ai-smoke.spec.js"
        smoke.write_text(
            "import { test, expect } from '@playwright/test';\n"
            "test('generated app renders', async ({ page }) => {\n"
            "  await page.goto('/');\n"
            "  await expect(page.locator('body')).toContainText(/.+/);\n"
            "});\n",
            encoding="utf-8",
        )
        return await self.runtime.run_command("cd frontend && npx playwright test tests/ise-ai-smoke.spec.js --reporter=line", timeout=240)

    def _file_payload(self, relative_path: str) -> dict[str, Any]:
        path = self.workspace / relative_path
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            content = ""
        return {"path": relative_path, "summary": self._summary_for_file(relative_path, content), "content": content, "language": self._language(relative_path)}

    def _summary_for_file(self, relative_path: str, content: str) -> str:
        if not content:
            return "Generated file."
        suffix = Path(relative_path).suffix.lower().lstrip(".")
        line_count = len(content.splitlines())
        return f"{suffix.upper() if suffix else 'Text'} file · {line_count} lines · {len(content.encode('utf-8'))} bytes"

    def _language(self, path: str) -> str:
        return {".jsx": "jsx", ".js": "javascript", ".tsx": "tsx", ".ts": "typescript", ".css": "css", ".scss": "scss", ".sass": "sass", ".json": "json", ".html": "html", ".md": "markdown", ".cs": "csharp", ".csproj": "xml", ".sql": "sql", ".yml": "yaml", ".yaml": "yaml"}.get(Path(path).suffix.lower(), "text")

    def _full_stack_login_plan(self, task: str, *, workspace_mode: str) -> list[dict[str, Any]]:
        """Build full-stack plans from the dynamic contract engine.

        The old implementation selected narrow blueprints and could still fall
        back to frontend/CV-shaped artifacts for non-login full-stack requests.
        This version derives every file from the runtime contract so a request
        like React + C# + MySQL webshop cannot export only App.jsx/App.css.
        """
        from app.services.dynamic_agent_runtime import get_dynamic_agent_runtime

        runtime = get_dynamic_agent_runtime()
        files = runtime.build_artifact_graph(task)
        contract = runtime.create_contract(task)
        plan: list[dict[str, Any]] = []
        for path, content in files.items():
            if path == "agent-contract.json":
                description = "Write dynamic task contract"
            elif path == "ROADMAP.md":
                description = "Write request-specific roadmap"
            elif path.startswith("frontend/"):
                description = "Write React frontend artifact from contract"
            elif path.startswith("backend/"):
                description = "Write backend/API artifact from contract"
            elif path.startswith("database/") or path == "docker-compose.yml":
                description = "Write database/runtime artifact from contract"
            else:
                description = f"Write {path}"
            plan.append({"agent": "BuilderAgent", "action": "write_file", "target": path, "description": description, "content": content})
        plan.append({"agent": "VerifierAgent", "action": "run_command", "target": "python3 scripts/verify_artifact.py", "description": "Verify dynamic artifact gates", "command": "python3 scripts/verify_artifact.py"})
        if "react" in contract.stacks:
            plan.append({"agent": "VerifierAgent", "action": "run_command", "target": "cd frontend && npm run build", "description": "Build React frontend", "command": "cd frontend && npm run build"})
        return plan

    async def _validate_requirements_before_export(self, task: str, paths: list[str]) -> None:
        if not _requires_full_stack(task):
            return
        required = {
            "React frontend": any(p.startswith("frontend/") and p.endswith((".jsx", ".json", ".html")) for p in paths),
            "C# backend": any(p.startswith("backend/") and p.endswith((".cs", ".csproj")) for p in paths),
            "MySQL schema": any(p.startswith("database/") and p.endswith(".sql") for p in paths),
            "verification script": any(p in {"scripts/verify_fullstack_artifact.py", "scripts/verify_artifact.py"} for p in paths),
        }
        missing = [name for name, ok in required.items() if not ok]
        if missing:
            raise RuntimeError("Export refused: full-stack request is missing " + ", ".join(missing))


    def _component_jsx(self, component_name: str, css_name: str, css_class: str, task: str) -> str:
        lower = task.lower()
        if "cart" in lower:
            return f"""import React, {{ useMemo, useState }} from \"react\";
import \"./{css_name}\";

const currency = new Intl.NumberFormat(\"en-US\", {{ style: \"currency\", currency: \"USD\" }});

export default function {component_name}({{ initialItems = [] }}) {{
  const [items, setItems] = useState(initialItems);

  const subtotal = useMemo(() => (
    items.reduce((total, item) => total + Number(item.price || 0) * Number(item.quantity || 1), 0)
  ), [items]);

  const updateQuantity = (id, nextQuantity) => {{
    setItems((current) =>
      current.map((item) =>
        item.id === id ? {{ ...item, quantity: Math.max(1, Number(nextQuantity) || 1) }} : item
      )
    );
  }};

  const removeItem = (id) => setItems((current) => current.filter((item) => item.id !== id));

  return (
    <section className=\"{css_class}\" aria-label=\"Shopping cart\">
      <header className=\"{css_class}__header\">
        <div>
          <p className=\"{css_class}__eyebrow\">Shopping cart</p>
          <h2>Your selected items</h2>
        </div>
        <span className=\"{css_class}__count\">{{items.length}} item{{items.length === 1 ? \"\" : \"s\"}}</span>
      </header>

      {{items.length === 0 ? (
        <div className=\"{css_class}__empty\">
          <strong>Your cart is empty.</strong>
          <p>Add products to see quantity controls, totals, and checkout actions.</p>
        </div>
      ) : (
        <div className=\"{css_class}__items\">
          {{items.map((item) => (
            <article className=\"{css_class}__item\" key={{item.id}}>
              <div>
                <strong>{{item.name}}</strong>
                {{item.description ? <p>{{item.description}}</p> : null}}
              </div>
              <div className=\"{css_class}__controls\">
                <input
                  aria-label={{`Quantity for ${{item.name}}`}}
                  type=\"number\"
                  min=\"1\"
                  value={{item.quantity || 1}}
                  onChange={{(event) => updateQuantity(item.id, event.target.value)}}
                />
                <span>{{currency.format(Number(item.price || 0) * Number(item.quantity || 1))}}</span>
                <button type=\"button\" onClick={{() => removeItem(item.id)}}>Remove</button>
              </div>
            </article>
          ))}}
        </div>
      )}}

      <footer className=\"{css_class}__footer\">
        <div>
          <span>Subtotal</span>
          <strong>{{currency.format(subtotal)}}</strong>
        </div>
        <button className=\"{css_class}__checkout\" type=\"button\" disabled={{items.length === 0}}>
          Checkout
        </button>
      </footer>
    </section>
  );
}}
"""
        body = "Hello World" if "hello world" in lower or "hellow world" in lower else _extract_subject(task)
        return f"""import React from \"react\";
import \"./{css_name}\";

export default function {component_name}() {{
  return (
    <section className=\"{css_class}\" aria-label=\"{body}\">
      <span className=\"{css_class}__badge\">React component</span>
      <h1>{body}</h1>
      <p>This component is focused, reusable, and packaged with its matching style file.</p>
    </section>
  );
}}
"""

    def _component_css(self, css_class: str) -> str:
        if "cart" in css_class:
            return f""".{css_class} {{
  width: min(760px, 100%);
  padding: 1.5rem;
  border-radius: 30px;
  color: #f8fafc;
  background: radial-gradient(circle at top left, rgba(34, 197, 94, 0.22), transparent 34%), linear-gradient(135deg, #0f172a, #182235);
  box-shadow: 0 28px 90px rgba(15, 23, 42, 0.32);
  animation: {css_class}-enter 520ms ease both;
}}

.{css_class}__header, .{css_class}__footer, .{css_class}__item, .{css_class}__controls {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}}

.{css_class}__header h2, .{css_class}__footer strong {{ margin: 0; }}
.{css_class}__eyebrow {{ margin: 0 0 0.25rem; color: #86efac; font-size: 0.75rem; font-weight: 900; letter-spacing: 0.16em; text-transform: uppercase; }}
.{css_class}__count {{ padding: 0.45rem 0.75rem; border-radius: 999px; background: rgba(255, 255, 255, 0.1); }}
.{css_class}__items {{ display: grid; gap: 0.85rem; margin: 1.25rem 0; }}
.{css_class}__item {{ padding: 1rem; border-radius: 22px; background: rgba(255, 255, 255, 0.075); border: 1px solid rgba(255, 255, 255, 0.1); animation: {css_class}-rise 460ms ease both; }}
.{css_class}__item p {{ margin: 0.3rem 0 0; color: rgba(226, 232, 240, 0.72); }}
.{css_class}__controls input {{ width: 4.5rem; padding: 0.55rem; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.2); background: rgba(15, 23, 42, 0.7); color: inherit; }}
.{css_class}__controls button, .{css_class}__checkout {{ border: 0; border-radius: 999px; padding: 0.7rem 1rem; font-weight: 800; cursor: pointer; transition: transform 180ms ease, opacity 180ms ease; }}
.{css_class}__controls button {{ color: #fecaca; background: rgba(248, 113, 113, 0.12); }}
.{css_class}__checkout {{ color: #052e16; background: #86efac; }}
.{css_class}__checkout:disabled {{ cursor: not-allowed; opacity: 0.45; }}
.{css_class}__controls button:hover, .{css_class}__checkout:not(:disabled):hover {{ transform: translateY(-2px); }}
.{css_class}__empty {{ margin: 1.25rem 0; padding: 1.25rem; border-radius: 22px; border: 1px dashed rgba(134, 239, 172, 0.35); color: rgba(226, 232, 240, 0.82); }}
@keyframes {css_class}-enter {{ from {{ opacity: 0; transform: scale(0.98); }} to {{ opacity: 1; transform: scale(1); }} }}
@keyframes {css_class}-rise {{ from {{ opacity: 0; transform: translateY(12px); }} to {{ opacity: 1; transform: translateY(0); }} }}
@media (max-width: 640px) {{ .{css_class}__header, .{css_class}__footer, .{css_class}__item, .{css_class}__controls {{ align-items: flex-start; flex-direction: column; }} }}
"""
        return f""".{css_class} {{
  min-height: 240px;
  display: grid;
  place-items: center;
  gap: 0.75rem;
  padding: 2rem;
  border-radius: 28px;
  color: #f8fafc;
  background: radial-gradient(circle at top left, rgba(56, 189, 248, 0.28), transparent 35%), linear-gradient(135deg, #0f172a, #1e293b);
  box-shadow: 0 28px 80px rgba(15, 23, 42, 0.35);
  text-align: center;
  animation: {css_class}-float 4s ease-in-out infinite;
}}
.{css_class} h1 {{ margin: 0; font-size: clamp(2.75rem, 8vw, 6rem); letter-spacing: -0.07em; }}
.{css_class} p {{ margin: 0; color: rgba(248, 250, 252, 0.78); }}
.{css_class}__badge {{ text-transform: uppercase; letter-spacing: 0.18em; color: #7dd3fc; font-weight: 900; }}
@keyframes {css_class}-float {{ 0%, 100% {{ transform: translateY(0); }} 50% {{ transform: translateY(-10px); }} }}
"""

    def _landing_app_jsx(self, subject: str, task: str) -> str:
        lower_subject = subject.lower()
        features = [
            ("Professional identity", f"The opening area introduces the {lower_subject} owner with role, strengths, and contact path."),
            ("Relevant CV structure", f"Sections organize profile, skills, achievements, experience, and footer contact details for {lower_subject}."),
            ("Hiring-focused next step", "Calls to action guide recruiters or clients toward email contact and experience review."),
        ]
        feature_js = json.dumps([{"title": a, "text": b} for a, b in features], indent=2)
        return f'''import React from "react";\nimport "./App.css";\n\nconst features = {feature_js};\n\nconst process = [\n  "Understand what visitors need first",\n  "Present the strongest value clearly",\n  "Guide users to the next action"\n];\n\nexport default function App() {{\n  return (\n    <main className="agentic-landing">\n      <nav className="top-nav">\n        <strong>{subject}</strong>\n        <a href="#contact">Contact</a>\n      </nav>\n\n      <section className="hero-grid">\n        <div className="hero-copy">\n          <p className="eyebrow">Professional CV landing page</p>\n          <h1>{subject}: professional profile, experience, skills, and contact.</h1>\n          <p className="lede">A complete CV landing page with header navigation, body sections, measurable highlights, and footer contact details.</p>\n          <div className="hero-actions">\n            <a className="primary-button" href="#contact">Hire me</a>\n            <a className="secondary-button" href="#features">View experience</a>\n          </div>\n        </div>\n        <aside className="showcase-card">\n          <span>Live-ready structure</span>\n          <strong>{subject}</strong>\n          <p>Responsive layout, visual hierarchy, animation, and clear CTAs.</p>\n        </aside>\n      </section>\n\n      <section id="features" className="section-block">\n        <p className="eyebrow">CV sections</p>\n        <h2>Built for recruiters, founders, and product teams reviewing a candidate quickly.</h2>\n        <div className="feature-grid">\n          {{features.map((feature) => (\n            <article className="feature-card" key={{feature.title}}>\n              <h3>{{feature.title}}</h3>\n              <p>{{feature.text}}</p>\n            </article>\n          ))}}\n        </div>\n      </section>\n\n      <section className="section-block split-section">\n        <div>\n          <p className="eyebrow">Roadmap implemented</p>\n          <h2>Plan, build, verify, export.</h2>\n        </div>\n        <ol className="process-list">\n          {{process.map((item) => <li key={{item}}>{{item}}</li>)}}\n        </ol>\n      </section>\n\n      <section id="contact" className="cta-section">\n        <p className="eyebrow">Final call to action</p>\n        <h2>Start a conversation about frontend, UI, and AI product work.</h2>\n        <p>Use this page as a polished candidate profile, then connect it to downloadable CV files or a portfolio CMS.</p>\n        <a className="primary-button" href="mailto:alex.morgan@career.local">Contact now</a>\n      </section>\n    </main>\n  );\n}}\n'''

    def _landing_css(self, subject: str) -> str:
        return '''.agentic-landing { min-height: 100vh; background: radial-gradient(circle at top left, rgba(14, 165, 233, 0.22), transparent 34%), radial-gradient(circle at 90% 10%, rgba(168, 85, 247, 0.18), transparent 28%), linear-gradient(135deg, #07111f, #111827 52%, #172033); color: #f8fafc; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }\n.top-nav, .hero-grid, .section-block, .cta-section { max-width: 1160px; margin: 0 auto; }\n.top-nav { display: flex; justify-content: space-between; align-items: center; padding: 1.2rem clamp(1.25rem, 4vw, 4rem); color: rgba(248,250,252,.78); }\n.top-nav a { color: inherit; text-decoration: none; }\n.hero-grid { display: grid; grid-template-columns: minmax(0, 1.08fr) minmax(280px, .72fr); gap: clamp(2rem, 6vw, 5rem); align-items: center; padding: 5rem clamp(1.25rem, 4vw, 4rem); }\n.eyebrow { margin: 0 0 .75rem; color: #67e8f9; font-size: .78rem; font-weight: 900; letter-spacing: .18em; text-transform: uppercase; }\n.hero-copy h1, .section-block h2, .cta-section h2 { margin: 0; letter-spacing: -.06em; line-height: .95; }\n.hero-copy h1 { max-width: 850px; font-size: clamp(3rem, 8vw, 7rem); }\n.section-block h2, .cta-section h2 { font-size: clamp(2rem, 5vw, 4.2rem); }\n.lede, .feature-card p, .cta-section p, .showcase-card p { color: rgba(226,232,240,.78); line-height: 1.75; font-size: 1.05rem; }\n.hero-actions { display: flex; flex-wrap: wrap; gap: 1rem; margin-top: 2rem; }\n.primary-button, .secondary-button { display: inline-flex; align-items: center; justify-content: center; border-radius: 999px; padding: .95rem 1.35rem; font-weight: 900; text-decoration: none; transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease; }\n.primary-button { background: #67e8f9; color: #06121f; box-shadow: 0 18px 45px rgba(103,232,249,.24); }\n.secondary-button { color: #f8fafc; border: 1px solid rgba(255,255,255,.2); background: rgba(255,255,255,.05); }\n.primary-button:hover, .secondary-button:hover { transform: translateY(-3px); }\n.showcase-card { min-height: 390px; display: grid; align-content: end; gap: .7rem; padding: 2rem; border-radius: 2rem; border: 1px solid rgba(255,255,255,.14); background: radial-gradient(circle at 35% 20%, rgba(103,232,249,.3), transparent 30%), linear-gradient(145deg, rgba(255,255,255,.12), rgba(255,255,255,.04)); box-shadow: 0 38px 100px rgba(0,0,0,.32); animation: float-card 4.8s ease-in-out infinite; }\n.showcase-card strong { font-size: clamp(2rem, 4vw, 3.5rem); line-height: 1; }\n.section-block { padding: 5rem clamp(1.25rem, 4vw, 4rem); }\n.feature-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1rem; margin-top: 2rem; }\n.feature-card, .process-list li { padding: 1.25rem; border-radius: 1.35rem; background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.11); animation: rise-in .56s ease both; }\n.split-section { display: grid; grid-template-columns: .9fr 1.1fr; gap: 2rem; align-items: start; }\n.process-list { display: grid; gap: 1rem; margin: 0; padding-left: 1.25rem; }\n.cta-section { margin-bottom: 4rem; padding: clamp(2rem, 5vw, 4rem); border-radius: 2rem; background: linear-gradient(135deg, rgba(103,232,249,.13), rgba(167,139,250,.14)); border: 1px solid rgba(255,255,255,.12); }\n@keyframes float-card { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-14px); } }\n@keyframes rise-in { from { opacity: 0; transform: translateY(18px); } to { opacity: 1; transform: translateY(0); } }\n@media (max-width: 860px) { .hero-grid, .split-section, .feature-grid { grid-template-columns: 1fr; } .top-nav { align-items: flex-start; flex-direction: column; } }\n'''
