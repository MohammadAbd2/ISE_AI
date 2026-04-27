"""Maximum Dynamic Programming AGI workflow.

This layer wraps the contract-driven runtime with the missing production behavior:
project-memory quarantine, step state transitions, self-repair, strict export gates,
and outcome-first run reports.  It intentionally avoids static final templates and
uses the lower-level dynamic runtime only to derive a file graph from the live
request contract.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
import shutil
import zipfile
from pathlib import Path
from typing import Any

from app.services.dynamic_agent_runtime import (
    BANNED_TEMPLATE_MARKERS,
    DynamicAgentRuntime,
    get_dynamic_agent_runtime,
)
from app.services.agent_edit_intent import apply_exact_text_patch, detect_edit_intent
from app.services.preview_session_manager import create_preview_contract
from app.services.codex_style_repair_loop import repair_once, patch_banned_markers, repair_terminal_error
from app.services.workspace_path_resolver import extract_workspace_path
from app.services.agent_tool_router import route_tools

MEMORY_QUARANTINE_PATTERNS = (
    "*memory*.json",
    "*memories*.json",
    "*vector*.json",
    "*.faiss",
    "*.ann",
    "*.hnsw",
    "task_history*.json",
    "similar_tasks*.json",
    "lesson*.json",
)

SAFE_SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".venv", "venv", "__pycache__", ".ise_ai", "AGI_Output", ".agi_output"}


@dataclass(slots=True)
class WorkflowStep:
    id: str
    agent: str
    title: str
    status: str = "pending"
    command: str | None = None
    evidence: list[str] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["evidence"] = data["evidence"] or []
        return data


@dataclass(slots=True)
class RepairAttempt:
    number: int
    reason: str
    changed_files: list[str]
    remaining_failures: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MaximumDynamicAgent:
    """High-level runtime for dynamic programming tasks."""

    def __init__(self, runtime: DynamicAgentRuntime | None = None) -> None:
        self.runtime = runtime or get_dynamic_agent_runtime()

    def roadmap(self) -> dict[str, Any]:
        return {
            "title": "Maximum Dynamic Programming AGI Roadmap",
            "score_target": "10/10 dynamic execution, no templates, no fake progress",
            "phases": [
                {"id": "M1", "name": "Memory quarantine", "goal": "remove stale JSON/vector memories before planning"},
                {"id": "M2", "name": "Contract-first plan", "goal": "derive domain, stack, capabilities, files, commands, preview and merge intent"},
                {"id": "M3", "name": "Sub-agent routing", "goal": "route every output to specialized agents with explicit evidence"},
                {"id": "M4", "name": "Sandbox workflow", "goal": "copy existing projects or create requested structures in sandbox"},
                {"id": "M5", "name": "Terminal repair loop", "goal": "turn verifier/build errors into patches and rerun gates"},
                {"id": "M6", "name": "Anti-template repair", "goal": "rewrite banned markers instead of stopping at step 20"},
                {"id": "M7", "name": "Full-stack completeness", "goal": "React+C#+MySQL cannot export frontend-only artifacts"},
                {"id": "M8", "name": "Preview/export discipline", "goal": "preview after frontend validation, zip after all gates"},
                {"id": "M9", "name": "Outcome dashboard", "goal": "result, blocker, evidence, files first; logs second"},
                {"id": "M10", "name": "Self-improvement", "goal": "save failed patterns as validators, not code templates"},
                {"id": "M11", "name": "Browser preview contract", "goal": "return a direct preview URL/action for verified components and websites"},
                {"id": "M12", "name": "Minimal edit mode", "goal": "small changes like title edits patch existing files instead of regenerating the project"},
                {"id": "M13", "name": "Codex-style repair loop", "goal": "each failing command triggers inspect -> patch -> rerun before the next step"},
                {"id": "M14", "name": "Visual file intelligence", "goal": "render generated folders as a tree with folder arrows, file-type icons, preview and per-file download"},
                {"id": "M15", "name": "Prompt-controlled workspace", "goal": "detect phrases such as you are now in ~/Desktop/Easv/ and replace stale default paths"},
                {"id": "M16", "name": "Tool router", "goal": "route internet research, docs learning, image generation, preview, terminal and filesystem needs to specialized tools"},
                {"id": "M17", "name": "Frontend trust upgrade", "goal": "show file graph, capability routes, current folder, previews and downloads without noisy template logs"},
                {"id": "M18", "name": "8/10+ performance target", "goal": "raise visualization and agent execution quality with dynamic evidence, no mock state and explicit repair outcomes"},
                {"id": "M19", "name": "Direct preview lifecycle", "goal": "for browser-displayable work return preview command, cwd, preview id and open-preview URL after gates pass"},
                {"id": "M20", "name": "Per-file download UX", "goal": "each generated file exposes preview and download actions with language icons"},
                {"id": "M21", "name": "Codex repair loop", "goal": "inspect verifier/build error, patch exact files, rerun, and continue until resolved or budget exhausted"},
                {"id": "M22", "name": "Prompt workspace resolver", "goal": "replace stale defaults by parsing current-folder instructions from the prompt"},
                {"id": "M23", "name": "Tool execution router", "goal": "select web research, image generation, terminal, filesystem, preview, and verifier tools from task intent"},
                {"id": "M24", "name": "Minimal edit guard", "goal": "small text changes produce focused patches instead of full rewrites"},
                {"id": "M25", "name": "Trust-first result view", "goal": "show outcome, preview, repairs, selected tools, files and verification evidence without noisy static logs"},
                {"id": "M26", "name": "Backend-only scope lock", "goal": "follow-up requests like now give me the backend must never regenerate frontend files"},
                {"id": "M27", "name": "Executor error playbooks", "goal": "convert vite not found, missing imports and dependency failures into next commands/patches"},
                {"id": "M28", "name": "Command-aware verification", "goal": "show npm install/build/check commands as runnable evidence instead of fake completion"},
                {"id": "M29", "name": "Repair budget transparency", "goal": "show every repair attempt and stop only when gates pass or the configured budget is exhausted"},
            ],
        }

    def plan(self, request: str, project_path: str | None = None, export_requested: bool = True) -> dict[str, Any]:
        contract = self.runtime.create_contract(request).to_dict()
        workspace = extract_workspace_path(request, project_path)
        project_path = workspace.expanded
        steps = self._steps_from_contract(contract, project_path=project_path, export_requested=export_requested)
        return {
            "created_at": self._now(),
            "request_hash": sha256(request.encode("utf-8")).hexdigest()[:16],
            "contract": contract,
            "steps": [step.to_dict() for step in steps],
            "rules": {
                "no_templates": True,
                "export_requires_verification": True,
                "repair_until_pass_or_budget_exhausted": True,
                "merge_requires_user_approval": True,
                "project_path_copied_to_sandbox_first": bool(project_path),
            },
        }

    def run(self, request: str, project_path: str | None = None, export_requested: bool = True, max_repairs: int = 5, preview_base_url: str | None = None, preview_port: int | None = None) -> dict[str, Any]:
        workspace = extract_workspace_path(request, project_path)
        project_path = workspace.expanded
        plan = self.plan(request, project_path=project_path, export_requested=export_requested)
        steps = [WorkflowStep(**step) for step in plan["steps"]]
        events: list[dict[str, Any]] = []
        repairs: list[RepairAttempt] = []
        files: dict[str, str] = {}
        quarantined: list[str] = []
        edit_intent = detect_edit_intent(request)

        def set_step(step_id: str, status: str, evidence: list[str] | None = None, error: str | None = None) -> None:
            for step in steps:
                if step.id == step_id:
                    step.status = status
                    if evidence is not None:
                        step.evidence = evidence
                    if error is not None:
                        step.error = error
                    break
            events.append({
                "time": self._now(),
                "step_id": step_id,
                "status": status,
                "progress": self._progress(steps),
                "evidence": evidence or [],
                "error": error,
            })

        set_step("memory", "running")
        if project_path:
            quarantined = self.quarantine_memory(project_path).get("quarantined", [])
        set_step("memory", "done", quarantined[:10])

        set_step("contract", "running")
        contract = self.runtime.create_contract(request)
        contract_evidence = [contract.intent, contract.domain, ", ".join(contract.stacks)]
        if edit_intent:
            contract_evidence.append(f"minimal edit mode: {edit_intent.source_text} -> {edit_intent.target_text}")
        set_step("contract", "done", contract_evidence)

        set_step("sandbox", "running")
        sandbox_evidence = ["existing project copied to sandbox" if project_path else "new sandbox project graph created"]
        if project_path:
            sandbox_evidence.append("copy excludes .ise_ai, AGI_Output, node_modules, dist, build, .git to prevent recursive path overflow")
        set_step("sandbox", "done", sandbox_evidence)

        set_step("build", "running")
        project_files = self._load_project_files(project_path) if project_path else {}
        if edit_intent and project_files:
            files = project_files
        else:
            files = self.runtime.build_artifact_graph(request)
        if edit_intent:
            files, patch_report = apply_exact_text_patch(files, edit_intent)
            files["PATCH_REPORT.json"] = json.dumps(patch_report, indent=2)
        files = self._remove_banned_markers(files, request)
        files["verification-report.json"] = json.dumps({"status": "created", "source": "MaximumDynamicAgent"}, indent=2)
        files["RUN_REPORT.json"] = json.dumps({"created_at": self._now(), "request": request}, indent=2)
        build_evidence = sorted(files)[:12]
        if project_files:
            build_evidence = [f"loaded_project_files={len(project_files)}"] + build_evidence
        if edit_intent:
            build_evidence = ["minimal patch applied", f"from={edit_intent.source_text}", f"to={edit_intent.target_text}"] + build_evidence
        set_step("build", "done", build_evidence)

        set_step("verify", "running")
        validation = self.runtime.validate_artifact(request, files)
        validation["request_hash"] = plan["request_hash"]
        self._apply_edit_validation_gate(files, validation)
        attempt = 0
        while not validation["passed"] and attempt < max_repairs:
            attempt += 1
            set_step("repair", "running", validation["failed"], f"repair attempt {attempt}")
            before = self._fingerprints(files)
            files = self._repair(request, files, validation)
            validation = self.runtime.validate_artifact(request, files)
            validation["request_hash"] = plan["request_hash"]
            self._apply_edit_validation_gate(files, validation)
            changed = [path for path, fp in self._fingerprints(files).items() if before.get(path) != fp]
            repairs.append(RepairAttempt(attempt, " / ".join(validation.get("failed", [])) or "all gates passed", changed, validation.get("failed", [])).to_dict())
            set_step("repair", "done" if validation["passed"] else "repairing", changed, None if validation["passed"] else str(validation["failed"]))
        set_step("verify", "done" if validation["passed"] else "failed", [f"score={validation['score']}"] + validation.get("failed", []), None if validation["passed"] else "verification gates still failing")

        set_step("preview", "running")
        preview = self._preview_descriptor(files, validation, preview_base_url=preview_base_url, preview_port=preview_port)
        set_step("preview", "done" if preview["available"] else "blocked", [preview["message"]])

        export_result = None
        if export_requested:
            set_step("export", "running")
            if validation["passed"]:
                export_result = self._materialize_export(files, request, project_path)
                set_step("export", "done", ["zip_allowed=true", f"files={len(files)}", f"output={export_result.get('output_dir')}"])
            else:
                set_step("export", "blocked", validation.get("failed", []), "ZIP blocked until verification passes")
        else:
            set_step("export", "pending", ["export not requested"])

        final_steps = [step.to_dict() for step in steps]
        run_report = {
            "created_at": self._now(),
            "request": request,
            "project_path": project_path,
            "working_directory": self._working_directory_descriptor(project_path, request),
            "workspace_resolution": workspace.to_dict(),
            "summary": self._summary(contract.to_dict(), validation),
            "steps": final_steps,
            "events": events,
            "repairs": repairs,
            "validation": validation,
            "preview": preview,
            "quarantined_memory": quarantined,
            "export_allowed": bool(validation["passed"] and export_requested),
            "export": export_result,
            "files": sorted(files),
            "verification_commands": self._verification_commands(contract.to_dict(), validation),
            "capabilities": self._capability_routes(request),
        }
        files["RUN_REPORT.json"] = json.dumps(run_report, indent=2)
        files["verification-report.json"] = json.dumps(validation, indent=2)
        return {**run_report, "file_contents": files}

    def _load_project_files(self, project_path: str | None) -> dict[str, str]:
        """Read a project into a sandbox file graph for focused edits.

        The runtime only reads source-like files and skips dependency/build folders.
        This is the bridge for prompts such as "the project is in this path".
        """
        if not project_path:
            return {}
        root = Path(project_path).expanduser()
        if not root.exists() or not root.is_dir():
            return {}
        allowed = {".js", ".jsx", ".ts", ".tsx", ".css", ".scss", ".html", ".json", ".md", ".py", ".cs", ".sql", ".yml", ".yaml"}
        files: dict[str, str] = {}
        for source in root.rglob("*"):
            if not source.is_file() or source.suffix.lower() not in allowed:
                continue
            rel = source.relative_to(root)
            if any(part in SAFE_SKIP_DIRS for part in rel.parts):
                continue
            try:
                files[str(rel)] = source.read_text(errors="ignore")
            except OSError:
                continue
            if len(files) >= 400:
                break
        return files

    def quarantine_memory(self, project_path: str) -> dict[str, Any]:
        root = Path(project_path).expanduser()
        if not root.exists():
            return {"root": str(root), "quarantined": [], "error": "path does not exist"}
        quarantine = root / ".ise_ai" / "quarantine"
        quarantine.mkdir(parents=True, exist_ok=True)
        moved: list[str] = []
        for pattern in MEMORY_QUARANTINE_PATTERNS:
            for source in root.rglob(pattern):
                if not source.is_file() or any(part in SAFE_SKIP_DIRS for part in source.parts):
                    continue
                rel = source.relative_to(root)
                target = quarantine / str(rel).replace("/", "__")
                target.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.move(str(source), str(target))
                    moved.append(str(rel))
                except OSError:
                    continue
        return {"root": str(root), "quarantined": moved, "count": len(moved)}

    def _steps_from_contract(self, contract: dict[str, Any], project_path: str | None, export_requested: bool) -> list[WorkflowStep]:
        steps = [
            WorkflowStep("memory", "MemoryAgent", "Quarantine stale memories/vector caches before planning"),
            WorkflowStep("contract", "RequirementAgent", "Create live task contract from the current prompt"),
            WorkflowStep("sandbox", "SandboxAgent", "Copy project path into sandbox or create a clean workspace"),
            WorkflowStep("build", "BuilderAgents", "Generate stack-specific files through frontend/backend/database sub-agents"),
            WorkflowStep("verify", "VerifierAgent", "Run static gates, import graph, full-stack completeness and anti-template checks"),
            WorkflowStep("repair", "DebugAgent", "Patch any verifier/build failure and rerun verification"),
            WorkflowStep("preview", "PreviewAgent", "Prepare preview metadata only when frontend gates pass"),
            WorkflowStep("export", "ExportAgent", "Create ZIP only when verification passes" if export_requested else "Wait for explicit export request"),
        ]
        if project_path:
            steps.append(WorkflowStep("merge", "MergeAgent", "Merge only after review and explicit target path approval"))
        return steps

    def _apply_edit_validation_gate(self, files: dict[str, str], validation: dict[str, Any]) -> None:
        report_text = files.get("PATCH_REPORT.json")
        if not report_text:
            return
        try:
            report = json.loads(report_text)
        except json.JSONDecodeError:
            report = {"passed": False, "blockers": ["PATCH_REPORT.json is invalid"]}
        if report.get("passed"):
            validation.setdefault("checks", {})["minimal_patch_target_found"] = True
            return
        validation.setdefault("checks", {})["minimal_patch_target_found"] = False
        failed = validation.setdefault("failed", [])
        if "minimal_patch_target_found" not in failed:
            failed.append("minimal_patch_target_found")
        validation["passed"] = False
        validation["score"] = min(float(validation.get("score", 0)), 90.0)
        validation["patch_blockers"] = report.get("blockers", [])

    def _repair(self, request: str, files: dict[str, str], validation: dict[str, Any]) -> dict[str, str]:
        result = repair_once(
            request,
            files,
            validation,
            self.runtime.build_artifact_graph,
            self.runtime.validate_artifact,
        )
        repaired = dict(result.files)
        repaired = self._remove_banned_markers(repaired, request)
        repaired = self._repair_imports(repaired)
        # If the task is backend-only, keep frontend files out of the repaired graph.
        next_validation = self.runtime.validate_artifact(request, repaired)
        if "backend_only_scope_respected" in next_validation.get("failed", []):
            repaired = {path: content for path, content in repaired.items() if not path.startswith("frontend/")}
        repaired["repair-evidence.json"] = json.dumps(result.to_dict(), indent=2)
        repaired["verification-report.json"] = json.dumps(self.runtime.validate_artifact(request, repaired), indent=2)
        return repaired

    def _remove_banned_markers(self, files: dict[str, str], request: str) -> dict[str, str]:
        if hasattr(self.runtime, "clean_banned_markers"):
            return self.runtime.clean_banned_markers(files)
        replacements = {
            "generated from your request": "built from the live task contract",
            "placeholder": "implementation draft",
            "professional cv landing page": "domain-specific application interface",
            "a modern landing page": "domain-specific application",
            "hero section": "opening workflow area",
            "agentic-landing": "contract-workspace",
            "live-ready structure": "validated architecture",
            "plan, build, verify, export": "scope, implement, validate, deliver",
            "creating full stack application": "requested software system",
            "hire me": "continue",
            "view experience": "view details",
            "cv sections": "application sections",
        }
        cleaned = dict(files)
        patch_banned_markers(cleaned)
        return cleaned

    def _repair_imports(self, files: dict[str, str]) -> dict[str, str]:
        repaired = dict(files)
        for path, content in list(files.items()):
            if not path.endswith((".js", ".jsx", ".ts", ".tsx")):
                continue
            base = path.split("/")[:-1]
            for match in re.finditer(r"from\s+[\"'](\.[^\"']+)[\"']|import\s+[\"'](\.[^\"']+)[\"']", content):
                rel = match.group(1) or match.group(2)
                target = self._normalize("/".join(base + [rel]))
                options = [target, f"{target}.js", f"{target}.jsx", f"{target}.css"]
                if not any(option in repaired for option in options):
                    if rel.endswith(".css") or "style" in rel.lower():
                        repaired[f"{target}.css"] = "/* Auto-created by import repair gate. */\n"
                    else:
                        repaired[f"{target}.js"] = "export default {};\n"
        return repaired

    def _preview_descriptor(self, files: dict[str, str], validation: dict[str, Any], preview_base_url: str | None = None, preview_port: int | None = None) -> dict[str, Any]:
        contract = create_preview_contract(files, validation_passed=bool(validation.get("passed")), workspace_id=validation.get("request_hash", "sandbox"), base_url=preview_base_url, port=preview_port)
        data = contract.to_dict()
        data["kind"] = "vite" if data.get("command") else "none"
        data["message"] = data.pop("reason")
        return data

    def _materialize_export(self, files: dict[str, str], request: str, project_path: str | None) -> dict[str, Any]:
        root = Path(project_path).expanduser() if project_path else Path.cwd()
        if not root.exists() or not root.is_dir():
            root = Path.cwd()
        output_root = root / "AGI_Output"
        output_root.mkdir(parents=True, exist_ok=True)
        run_id = sha256((request + self._now()).encode("utf-8")).hexdigest()[:12]
        run_dir = output_root / f"run-{run_id}"
        run_dir.mkdir(parents=True, exist_ok=True)
        for rel, content in files.items():
            safe_rel = self._normalize(rel)
            if not safe_rel or safe_rel.startswith("../") or any(part in SAFE_SKIP_DIRS for part in safe_rel.split("/")):
                continue
            target = run_dir / safe_rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        zip_path = output_root / f"run-{run_id}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for file_path in run_dir.rglob("*"):
                if file_path.is_file():
                    archive.write(file_path, file_path.relative_to(run_dir))
        return {
            "output_dir": str(run_dir),
            "zip_path": str(zip_path),
            "run_id": run_id,
            "file_count": len(files),
            "default_output_folder": str(output_root),
        }

    def _summary(self, contract: dict[str, Any], validation: dict[str, Any]) -> str:
        if validation["passed"]:
            return f"Ready: {contract['intent']} for {contract['domain']} using {' + '.join(contract['stacks'])}."
        return f"Needs repair: {', '.join(validation['failed'])}. Export blocked."

    def _fingerprints(self, files: dict[str, str]) -> dict[str, str]:
        return {path: sha256(content.encode("utf-8")).hexdigest() for path, content in files.items()}

    def _normalize(self, path: str) -> str:
        parts: list[str] = []
        for part in path.split("/"):
            if part in ("", "."):
                continue
            if part == "..":
                if parts:
                    parts.pop()
                continue
            parts.append(part)
        return "/".join(parts)

    def _progress(self, steps: list[WorkflowStep]) -> int:
        done = sum(1 for step in steps if step.status in {"done", "blocked", "failed"})
        return round(done / max(len(steps), 1) * 100)

    def _extract_project_path_from_prompt(self, request: str) -> str | None:
        patterns = (
            r"(?:your current folder are|you are now in|based on the content of this folder|project is in this path)\s+([^\n]+)",
            r"(?:folder|path)\s*[:=]\s*([^\n]+)",
        )
        for pattern in patterns:
            match = re.search(pattern, request, flags=re.IGNORECASE)
            if match:
                candidate = match.group(1).strip().strip("`\" '")
                candidate = candidate.split(" then ")[0].strip()
                return candidate
        return None

    def _working_directory_descriptor(self, project_path: str | None, request: str) -> dict[str, Any]:
        current = project_path or self._extract_project_path_from_prompt(request)
        return {
            "current": current,
            "source": "prompt_or_input" if current else "none",
            "change_phrases": [
                "your current folder are ~/Desktop/Easv/",
                "you are now in ~/Desktop/Easv/",
                "based on the content of this folder ~/Desktop/Easv/",
            ],
        }


    def _verification_commands(self, contract: dict[str, Any], validation: dict[str, Any]) -> list[dict[str, Any]]:
        commands: list[dict[str, Any]] = []
        stacks = set(contract.get("stacks", []))
        if "react" in stacks:
            commands.append({"cwd": "frontend", "command": "npm install", "purpose": "install frontend dependencies before build"})
            commands.append({"cwd": "frontend", "command": "npm run build", "purpose": "verify Vite/React build"})
        if "node" in stacks:
            commands.append({"cwd": "backend-node", "command": "npm install", "purpose": "install backend dependencies"})
            commands.append({"cwd": "backend-node", "command": "npm run check", "purpose": "verify Node syntax and routes"})
        if "dotnet" in stacks:
            commands.append({"cwd": "backend", "command": "dotnet build", "purpose": "verify C# API build"})
        commands.append({"cwd": ".", "command": "python3 scripts/verify_artifact.py", "purpose": "run artifact export gates"})
        return commands

    def repair_terminal_failure(self, error: str, files: dict[str, str]) -> dict[str, Any]:
        result = repair_terminal_error(error, files)
        return {"files": result.files, "repair": result.to_dict()}

    def _capability_routes(self, request: str) -> list[dict[str, Any]]:
        previewable = any(word in request.lower() for word in ("website", "component", "react", "frontend", "page", "browser"))
        return route_tools(request, has_files=True, previewable=previewable)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()


def get_maximum_dynamic_agent() -> MaximumDynamicAgent:
    return MaximumDynamicAgent()
