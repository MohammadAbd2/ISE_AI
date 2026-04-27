from __future__ import annotations

import filecmp
import json
import shutil
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import settings
from app.services.intelligent_coding_agent import IntelligentCodingAgent
from app.services.planning_agent import AutonomousPlanningAgent, ExecutionPlan, PlanStep
from app.services.plan_checkpoint import load_checkpoint
from app.services.project_exports import get_project_export_service
from app.services.autonomous_loop_engine import AutonomousLoopEngine


@dataclass(slots=True)
class SelfUpgradeExecutionResult:
    reply: str
    render_blocks: list[dict]
    used_agents: list[str]




def safe_export_name(summary: str, fallback: str = 'generated-output') -> str:
    slug = ''.join(ch.lower() if ch.isalnum() else '-' for ch in summary[:80]).strip('-')
    slug = '-'.join(part for part in slug.split('-') if part)
    return slug or fallback


def branch_label_from_summary(summary: str) -> str:
    return safe_export_name(summary, fallback='sandbox-output').replace('-', ' ').title()


def _guess_language_from_path(path: str) -> str:
    suffix = Path(path).suffix.lower()
    return {'.js': 'javascript', '.jsx': 'jsx', '.ts': 'typescript', '.tsx': 'tsx', '.py': 'python', '.css': 'css', '.html': 'html', '.json': 'json', '.md': 'markdown'}.get(suffix, 'text')


def derive_export_label(paths: list[str], fallback: str = 'generated-output') -> str:
    names = [Path(path).stem for path in paths if path]
    if not names:
        return fallback
    unique = []
    for name in names:
        if name not in unique:
            unique.append(name)
    return '-'.join(unique[:3]) if len(unique) > 1 else unique[0]


class SelfUpgradeExecutor:
    """Run self-upgrade work against an isolated project copy before any merge."""

    _IGNORE_PATTERNS = (
        ".git",
        "node_modules",
        "dist",
        "__pycache__",
        ".pytest_cache",
        "*.pyc",
        "venv",
        ".venv",
        "external",
        ".idea",
        ".qwen",
        "*.db",
        "*.sqlite",
        ".eval-history.json",
        ".execution-packet-history.json",
        ".ise_ai_self_rewrites",
        "output",
    )

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = (project_root or Path(settings.project_root)).resolve()
        default_output_root = Path(getattr(settings, "output_path", self.project_root / "output")).resolve()
        if str(default_output_root).startswith(str(self.project_root)):
            default_output_root = (Path.home() / ".cache" / "ise_ai" / "runtime").resolve()
        self.output_root = default_output_root
        self.sandbox_root = self.output_root / "sandboxes"
        self.sandbox_root.mkdir(parents=True, exist_ok=True)

    async def execute_packet(self, packet: dict, session_id: str | None = None, progress_callback=None) -> SelfUpgradeExecutionResult:
        branch_label = f"sandbox-task-{packet.get('packet_id', 'draft')}"
        apply_on_success = bool(packet.get("apply_on_success"))

        sandbox_id = packet.get("packet_id", "draft")
        sandbox_dir = self.sandbox_root / f"sandbox-{sandbox_id}"
        sandbox_path = sandbox_dir / "workspace"
        if sandbox_dir.exists():
            shutil.rmtree(sandbox_dir, ignore_errors=True)
        sandbox_dir.mkdir(parents=True, exist_ok=True)

        workspace_mode = self._determine_workspace_mode(packet)
        self._prepare_workspace(packet=packet, sandbox_path=sandbox_path, workspace_mode=workspace_mode)
        if workspace_mode == "project_copy":
            self._reattach_local_dependencies(sandbox_path)

        use_autonomous_loop = packet.get("task_mode") == "user_task" and packet.get("use_autonomous_loop", True)
        if use_autonomous_loop:
            engine = AutonomousLoopEngine(workspace=sandbox_path, session_id=session_id, progress_callback=progress_callback)
            loop_result = await engine.run(str(packet.get("summary") or packet.get("task") or ""), workspace_mode=workspace_mode)
            status = loop_result.status
            changed_files = loop_result.changed_files
            approval_request = None
            execution_steps = loop_result.steps
            summary = loop_result.summary
        else:
            planning_agent = AutonomousPlanningAgent(project_root=sandbox_path, auto_commit_workspace=False)
            coding_agent = IntelligentCodingAgent(project_root=sandbox_path)
            structured_plan = self._build_execution_plan(packet)

            if structured_plan is not None:
                async def _emit_plan_progress(plan_or_block):
                    if not progress_callback:
                        return
                    if isinstance(plan_or_block, dict):
                        await progress_callback(plan_or_block)
                        return
                    await progress_callback(self._build_plan_progress_block(plan_or_block))

                plan = await planning_agent.execute_plan(structured_plan, progress_callback=_emit_plan_progress)
                status = plan.status.value
                committed_to_sandbox: list[str] = []
                try:
                    workspace = getattr(planning_agent.coding_agent, "workspace", None)
                    if status == "completed" and workspace is not None and getattr(planning_agent.coding_agent, "use_workspace", False):
                        committed_to_sandbox = workspace.commit_to(sandbox_path)
                except Exception:
                    committed_to_sandbox = []
                changed_files = self._collect_changed_files(sandbox_path)
                if not changed_files and committed_to_sandbox:
                    changed_files = [{"path": path, "summary": "Generated inside isolated sandbox."} for path in committed_to_sandbox]
                if not changed_files and status == "completed":
                    target_paths = []
                    for step in plan.steps:
                        if step.action_type in {"create_file", "edit_file"}:
                            target = str(step.target or "").strip().lstrip("/")
                            if target and (sandbox_path / target).is_file():
                                target_paths.append(target)
                    changed_files = [{"path": path, "summary": "Verified generated file."} for path in dict.fromkeys(target_paths)]
                approval_request = self._build_approval_request(plan)
                execution_steps = [
                    {
                        "step_number": step.step_number,
                        "description": step.description,
                        "status": step.status.value,
                        "target": ("ZIP artifact" if step.action_type == "export_artifact" else step.target),
                        "agent": step.metadata.get("agent") or {
                            "create_file": "BuilderAgent",
                            "edit_file": "BuilderAgent",
                            "run_command": "VerifierAgent",
                            "export_artifact": "ExportAgent",
                        }.get(step.action_type, "PlannerAgent"),
                        "output": step.output[:240] if step.output else "",
                        "error": step.error[:240] if step.error else "",
                    }
                    for step in plan.steps
                ]
                summary = f"Isolated execution finished with {plan.completed_steps}/{plan.total_steps} completed steps."
            else:
                prompt = self._build_isolated_task_prompt(packet)
                progress = await coding_agent.execute_task(prompt, project_context={})
                status = progress.overall_status
                changed_files = self._collect_changed_files(sandbox_path)
                approval_request = None
                execution_steps = [
                    {
                        "step_number": index + 1,
                        "description": action.description,
                        "status": action.status.value,
                        "target": action.target,
                        "agent": "BuilderAgent",
                        "output": action.output[:240] if action.output else "",
                        "error": action.error[:240] if action.error else "",
                    }
                    for index, action in enumerate(progress.actions)
                ]
                summary = progress.message

        applied_files: list[str] = []
        if apply_on_success and status == "completed":
            applied_files = self._apply_changed_files(sandbox_path)

        export_artifact = None
        export_summary = None
        if session_id and changed_files:
            try:
                export_result, export_summary = await self._export_for_task(
                    packet=packet,
                    sandbox_path=sandbox_path,
                    changed_files=changed_files,
                    session_id=session_id,
                    branch_label=branch_label,
                )
                export_artifact = export_result.artifact if export_result else None
            except Exception as exc:
                export_artifact = None
                export_summary = {"mode": "error", "description": f"Export failed: {exc}", "paths": []}

        self._write_sandbox_metadata(
            sandbox_dir=sandbox_dir,
            branch_label=branch_label,
            packet=packet,
            status=status,
            changed_files=changed_files,
            applied_files=applied_files,
            export_artifact=export_artifact,
            export_summary=export_summary,
        )

        blocks = self._build_render_blocks(
            packet=packet,
            branch_label=branch_label,
            status=status,
            summary=summary,
            changed_files=changed_files,
            execution_steps=execution_steps,
            applied_files=applied_files,
            approval_request=approval_request,
            sandbox_path=sandbox_path,
            export_artifact=export_artifact,
            export_summary=export_summary,
        )
        merge_ready = status == "completed"
        reply = (
            f"Ran the task in isolated sandbox `{branch_label}`. "
            f"Status: {status}. Changed files: {len(changed_files)}. "
            f"Applied to main project: {'yes' if applied_files else 'no'}. Merge ready: {'yes' if merge_ready else 'no'}. "
            f"Sandbox workspace: `{sandbox_path}`."
        )
        return SelfUpgradeExecutionResult(
            reply=reply,
            render_blocks=blocks,
            used_agents=["PlannerAgent", "BuilderAgent", "VerifierAgent", "DebugAgent", "ExportAgent"],
        )

    def _build_isolated_task_prompt(self, packet: dict) -> str:
        subsystem = packet.get("subsystem") or "self-improvement"
        targets = packet.get("targets", [])
        if isinstance(targets, list):
            targets_str = ", ".join(str(t) for t in targets[:6])
        else:
            targets_str = str(targets)

        verification = packet.get("verification", [])
        summary = packet.get("summary") or "Apply the current self-improvement packet."
        steps = packet.get("steps", [])
        
        lines = [
            f"Implement the current {subsystem} task in this isolated project copy.",
            summary,
        ]
        if targets_str:
            lines.append(f"Focus on these files or areas first: {targets_str}.")
        
        if steps and isinstance(steps, list):
            lines.append("Follow this plan:")
            for step in steps:
                if isinstance(step, dict):
                    desc = step.get("description") or step.get("step") or str(step)
                else:
                    desc = str(step)
                lines.append(f"- {desc}")
        
        if verification and isinstance(verification, list):
            lines.append("After the code changes, run these verification commands:")
            for command in verification:
                if isinstance(command, str) and command.strip():
                    lines.append(f"- {command.strip()}")
        
        lines.append("Do not just describe the work. Make the code changes, run verification, and report the result.")
        return "\n".join(lines)

    def _build_execution_plan(self, packet: dict) -> ExecutionPlan | None:
        structured_steps = packet.get("plan_steps")
        summary = packet.get("summary") or "Execute the current sandbox task."
        if isinstance(structured_steps, list) and structured_steps:
            plan = ExecutionPlan(task=summary, created_at=datetime.now(UTC).isoformat())
            packet_id = str(packet.get("packet_id") or plan.id)
            plan.id = packet_id
            setattr(plan, "_checkpoint_id", packet_id)
            plan.steps = [
                PlanStep(
                    step_number=index + 1,
                    description=str(step.get("description", "")),
                    action_type=str(step.get("action_type", "general")),
                    target=str(step.get("target", "")),
                    metadata=step.get("metadata", {}) if isinstance(step.get("metadata", {}), dict) else {},
                )
                for index, step in enumerate(structured_steps)
                if isinstance(step, dict) and str(step.get("description", "")).strip()
            ]
            return plan if plan.steps else None

        steps = packet.get("steps", [])
        summary = packet.get("summary") or "Apply the current self-improvement packet."
        verification_commands = [
            command.strip()
            for command in (packet.get("verification", []) or [])
            if isinstance(command, str) and command.strip()
        ]
        packet_targets = [
            target
            for target in (packet.get("targets", []) or [])
            if isinstance(target, str) and target.strip()
        ]

        if not isinstance(steps, list) or not steps:
            return None

        plan = ExecutionPlan(task=summary, created_at=datetime.now(UTC).isoformat())
        plan_steps: list[PlanStep] = []
        step_number = 1

        for step in steps:
            description = self._normalize_step_description(step)
            if not description:
                continue
            action_type, target = self._classify_packet_step(description, verification_commands)
            plan_steps.append(
                PlanStep(
                    step_number=step_number,
                    description=description,
                    action_type=action_type,
                    target=target,
                    metadata={
                        "packet_step": True,
                        "packet_targets": packet_targets,
                        "packet_verification_commands": verification_commands,
                        "packet_subsystem": packet.get("subsystem", ""),
                    },
                )
            )
            step_number += 1

        for command in verification_commands:
            if command:
                plan_steps.append(
                    PlanStep(
                        step_number=step_number,
                        description=f"Verify the generated changes with `{command}`",
                        action_type="run_command",
                        target=command,
                        metadata={
                            "verification": True,
                            "packet_step": True,
                            "packet_targets": packet_targets,
                            "packet_verification_commands": verification_commands,
                            "packet_subsystem": packet.get("subsystem", ""),
                        },
                    )
                )
                step_number += 1

        if not plan_steps:
            return None

        plan.steps = plan_steps
        return plan

    def _normalize_step_description(self, step: object) -> str:
        if isinstance(step, dict):
            return str(step.get("description") or step.get("step") or "").strip()
        if isinstance(step, str):
            return step.strip()
        return ""

    def _classify_packet_step(self, description: str, verification_commands: list[str]) -> tuple[str, str]:
        lower = description.lower()
        target = ""

        if any(keyword in lower for keyword in ("verify", "test", "build", "compileall", "pytest", "npm run", "run ")):
            target = self._extract_verification_target(description)
            if not target:
                target = self._match_packet_verification_command(description, verification_commands)
            return "run_command", target

        if any(keyword in lower for keyword in ("inspect", "open", "review", "analyze", "diagnose")):
            target = self._extract_focus_target(description)
            return ("read_file" if target else "general"), target

        if any(keyword in lower for keyword in ("edit", "update", "fix", "patch", "implement", "change")):
            target = self._extract_focus_target(description)
            return ("edit_file" if target else "general"), target

        return "general", target

    def _extract_verification_target(self, description: str) -> str:
        backtick_match = description.split("`")
        if len(backtick_match) >= 3:
            return backtick_match[1].strip()

        command_match = None
        for pattern in (
            r"(PYTHONPATH=[^\n]+pytest[^\n]*)",
            r"(cd\s+[^\n]+&&\s+[^\n]+)",
            r"(python(?:3(?:\.\d+)?)?\s+-m\s+[^\n]+)",
            r"(npm\s+run\s+\w+)",
        ):
            command_match = __import__("re").search(pattern, description)
            if command_match:
                return command_match.group(1).strip()
        return ""

    def _extract_focus_target(self, description: str) -> str:
        import re

        match = re.search(r"([\w./-]+\.(?:py|jsx|tsx|js|ts|css|html|json|md))", description)
        if match:
            return match.group(1)
        return ""

    def _match_packet_verification_command(self, description: str, verification_commands: list[str]) -> str:
        lower = description.lower()
        if not verification_commands:
            return ""

        keyword_groups = [
            (("eval", "pytest", "test suite", "internal eval"), ("pytest",)),
            (("build", "frontend", "vite"), ("npm run build", "vite build")),
            (("compile", "syntax", "backend"), ("compileall",)),
        ]
        for intent_keywords, command_markers in keyword_groups:
            if any(keyword in lower for keyword in intent_keywords):
                for command in verification_commands:
                    command_lower = command.lower()
                    if any(marker in command_lower for marker in command_markers):
                        return command

        return verification_commands[0]

    def _reattach_local_dependencies(self, sandbox_path: Path) -> None:
        frontend_root = self.project_root / "frontend"
        sandbox_frontend = sandbox_path / "frontend"
        source_node_modules = frontend_root / "node_modules"
        sandbox_node_modules = sandbox_frontend / "node_modules"

        if not source_node_modules.exists() or sandbox_node_modules.exists():
            return
        if not sandbox_frontend.exists():
            return

        try:
            sandbox_node_modules.symlink_to(source_node_modules, target_is_directory=True)
        except OSError:
            # Fall back to a shallow copy when symlinks are unavailable in the runtime.
            shutil.copytree(source_node_modules, sandbox_node_modules, dirs_exist_ok=True)

    def _is_multi_step(self, prompt: str) -> bool:
        lower = prompt.lower()
        markers = ("then", "after that", "step 1", "step 2", "verification commands", "follow this plan")
        return any(marker in lower for marker in markers)

    def _determine_workspace_mode(self, packet: dict) -> str:
        summary = str(packet.get("summary") or "").lower()
        markers = ("landing page", "website", "full project", "entire project", "application", "restaurant")
        if any(marker in summary for marker in markers):
            return "project_copy"
        for step in packet.get("plan_steps", []) or []:
            if not isinstance(step, dict):
                continue
            target = str(step.get("target") or "")
            if target.startswith(("backend/", "frontend/", "docs/")) and ("package.json" in target or target.count('/') > 2):
                if any(marker in summary for marker in ("app", "project", "frontend", "backend")):
                    return "project_copy"
        return "focused"

    def _prepare_workspace(self, *, packet: dict, sandbox_path: Path, workspace_mode: str) -> None:
        if workspace_mode == "project_copy":
            shutil.copytree(
                self.project_root,
                sandbox_path,
                ignore=shutil.ignore_patterns(*self._IGNORE_PATTERNS),
            )
            return

        sandbox_path.mkdir(parents=True, exist_ok=True)
        targets: list[str] = []
        for step in packet.get("plan_steps", []) or []:
            if not isinstance(step, dict):
                continue
            target = str(step.get("target") or "").strip().lstrip("/")
            if target and "." in Path(target).name:
                targets.append(target)
        for target in targets:
            (sandbox_path / target).parent.mkdir(parents=True, exist_ok=True)

    def _collect_changed_files(self, sandbox_path: Path) -> list[dict]:
        changed: list[dict] = []
        comparison = filecmp.dircmp(self.project_root, sandbox_path, ignore=list(self._IGNORE_PATTERNS))
        for relative in self._walk_diff(comparison):
            candidate = sandbox_path / relative
            if candidate.is_dir():
                continue
            try:
                content = candidate.read_text(encoding="utf-8")
                summary = content[:320]
            except Exception:
                content = None
                summary = "Changed in isolated environment."
            changed.append({"path": relative.as_posix(), "summary": summary, "content": content, "language": _guess_language_from_path(relative.as_posix())})
        return changed[:20]

    def _walk_diff(self, comparison: filecmp.dircmp, prefix: Path | None = None) -> list[Path]:
        prefix = prefix or Path()
        changed = [prefix / name for name in comparison.diff_files + comparison.right_only]
        for name, subdir in comparison.subdirs.items():
            if name in set(self._IGNORE_PATTERNS):
                continue
            changed.extend(self._walk_diff(subdir, prefix / name))
        return changed

    def _apply_changed_files(self, sandbox_path: Path) -> list[str]:
        changed_files = self._collect_changed_files(sandbox_path)
        applied: list[str] = []
        for item in changed_files:
            relative_path = Path(item["path"])
            source = sandbox_path / relative_path
            destination = self.project_root / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            if source.exists():
                shutil.copy2(source, destination)
                applied.append(relative_path.as_posix())
        return applied

    def _build_plan_progress_block(self, plan: ExecutionPlan) -> dict:
        steps = []
        for step in plan.steps[:20]:
            steps.append({
                "step_number": step.step_number,
                "description": step.description,
                "status": step.status.value,
                "target": step.target,
                "output": step.output[:160] if step.output else "",
                "error": step.error[:160] if step.error else "",
            })
        elapsed_seconds = 0
        try:
            if plan.started_at:
                elapsed_seconds = max(0, int((datetime.now(UTC) - datetime.fromisoformat(plan.started_at)).total_seconds()))
        except Exception:
            elapsed_seconds = 0
        estimated_seconds = max(30, len(plan.steps) * 45)
        return {
            "type": "plan_result",
            "payload": {
                "title": "Sandbox execution progress",
                "status": plan.status.value,
                "steps": steps,
                "timing": {"elapsed_seconds": elapsed_seconds, "estimated_seconds": estimated_seconds},
            },
        }

    def _build_approval_request(self, plan: ExecutionPlan) -> dict | None:
        checkpoint_id = getattr(plan, "_checkpoint_id", None)
        if not checkpoint_id or plan.status.value != "pending":
            return None
        try:
            checkpoint = load_checkpoint(checkpoint_id)
        except Exception:
            checkpoint = {}

        blocked_step = None
        for step in checkpoint.get("steps", []):
            metadata = step.get("metadata") or {}
            if metadata.get("requires_approval"):
                blocked_step = step
                break

        if blocked_step is None:
            return None

        return {
            "plan_id": checkpoint_id,
            "task": checkpoint.get("task") or plan.task,
            "step_number": blocked_step.get("step_number"),
            "step_description": blocked_step.get("description", ""),
            "approval_reason": (blocked_step.get("metadata") or {}).get("approval_reason", blocked_step.get("error", "")),
            "staged_diffs": checkpoint.get("staged_diffs", []),
        }


    async def _export_for_task(
        self,
        *,
        packet: dict,
        sandbox_path: Path,
        changed_files: list[dict],
        session_id: str,
        branch_label: str,
    ):
        exporter = get_project_export_service()
        selection = self._determine_export_selection(packet, changed_files)
        mode = selection["mode"]
        paths = selection["paths"]
        title = selection["title"]
        filename = selection["filename"]
        description = selection["description"]
        package_root = selection.get("package_root") or branch_label
        if mode == "directory":
            export_dir = sandbox_path if package_root == "." else sandbox_path / package_root
            result = await exporter.export_directory(
                source_dir=export_dir,
                session_id=session_id,
                title=title,
                filename=filename,
            )
        else:
            result = await exporter.export_paths(
                root_dir=sandbox_path,
                relative_paths=paths,
                extra_include_paths=selection.get("extra_include_paths", []),
                session_id=session_id,
                title=title,
                filename=filename,
                package_root=package_root,
            )
        return result, {"mode": mode, "description": description, "paths": paths, "package_root": package_root}

    def _determine_export_selection(self, packet: dict, changed_files: list[dict]) -> dict:
        summary = str(packet.get("summary") or "")
        lower = summary.lower()
        changed_paths = [item.get("path", "") for item in changed_files if item.get("path")]
        changed_paths = [path for path in changed_paths if path and not path.startswith("backend/.ise_ai_checkpoints")]
        packet_targets = []
        for step in packet.get("plan_steps", []) or []:
            if isinstance(step, dict):
                target = str(step.get("target") or "").strip().lstrip("/")
                if target and "." in Path(target).name:
                    packet_targets.append(target)
        candidate_paths = list(dict.fromkeys(changed_paths + packet_targets))
        frontend_paths = [p for p in candidate_paths if p.startswith("frontend/")]
        backend_paths = [p for p in candidate_paths if p.startswith("backend/")]

        project_markers = ["landing page", "restaurant", "website", "web app", "entire project", "full project", "application", " app "]
        wants_full_project = any(marker in lower for marker in project_markers)
        only_small_file_bundle = len(candidate_paths) <= 4 and not wants_full_project
        export_label = derive_export_label(candidate_paths, fallback=safe_export_name(summary, fallback="generated-output"))

        if wants_full_project:
            if frontend_paths and len(frontend_paths) >= len(backend_paths):
                extra_include = [
                    "frontend/package.json",
                    "frontend/package-lock.json",
                    "frontend/index.html",
                    "frontend/vite.config.js",
                    "frontend/src/main.jsx",
                    "frontend/src/main.js",
                ]
                return {
                    "mode": "paths",
                    "package_root": "generated-react-project",
                    "title": f"{export_label} React project",
                    "filename": f"{safe_export_name(export_label, fallback='generated-react-project')}.zip",
                    "description": "Download the generated React project as a focused ZIP archive.",
                    "paths": frontend_paths,
                    "extra_include_paths": extra_include,
                }
            return {
                "mode": "directory",
                "package_root": ".",
                "title": f"{export_label} project",
                "filename": f"{safe_export_name(export_label, fallback='generated-project')}.zip",
                "description": "Download the generated project as a ZIP archive.",
                "paths": candidate_paths,
            }

        if only_small_file_bundle:
            extra_include = []
            return {
                "mode": "paths",
                "package_root": "generated-files",
                "title": f"{export_label} files",
                "filename": f"{safe_export_name(export_label, fallback='generated-files')}.zip",
                "description": f"Download the generated file bundle as a ZIP archive ({len(candidate_paths)} file{'s' if len(candidate_paths) != 1 else ''}).",
                "paths": candidate_paths,
                "extra_include_paths": extra_include,
            }

        dominant_root = None
        root_counts = Counter(path.split('/', 1)[0] for path in candidate_paths if '/' in path)
        if root_counts:
            dominant_root = root_counts.most_common(1)[0][0]
        if dominant_root == 'frontend':
            return {
                "mode": "directory",
                "package_root": "frontend",
                "title": f"{export_label} frontend",
                "filename": f"{safe_export_name(export_label, fallback='frontend-export')}.zip",
                "description": "Download the generated frontend workspace as a ZIP archive.",
                "paths": candidate_paths,
            }
        return {
            "mode": "paths",
            "package_root": "generated-files",
            "title": f"{export_label} files",
            "filename": f"{safe_export_name(export_label, fallback='generated-files')}.zip",
            "description": f"Download the generated output as a ZIP archive ({len(candidate_paths)} files).",
            "paths": candidate_paths,
        }


    def _write_sandbox_metadata(
        self,
        *,
        sandbox_dir: Path,
        branch_label: str,
        packet: dict,
        status: str,
        changed_files: list[dict],
        applied_files: list[str],
        export_artifact: dict | None,
        export_summary: dict | None,
    ) -> None:
        metadata = {
            "branch_label": branch_label,
            "packet_id": packet.get("packet_id"),
            "status": status,
            "created_at": datetime.now(UTC).isoformat(),
            "workspace": str(sandbox_dir / "workspace"),
            "changed_files": changed_files,
            "applied_files": applied_files,
            "export_artifact": export_artifact,
            "export_summary": export_summary,
        }
        (sandbox_dir / "sandbox.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    def _build_render_blocks(
        self,
        *,
        packet: dict,
        branch_label: str,
        status: str,
        summary: str,
        changed_files: list[dict],
        execution_steps: list[dict],
        applied_files: list[str],
        approval_request: dict | None,
        sandbox_path: Path,
        export_artifact: dict | None,
        export_summary: dict | None,
    ) -> list[dict]:
        merge_ready = status == "completed"
        generated_at = datetime.now(UTC).isoformat()
        blocks = [
            {
                "type": "report",
                "payload": {
                    "title": "Isolated sandbox run",
                    "summary": summary,
                    "highlights": [
                        f"Environment: {branch_label}",
                        f"Packet: {packet.get('packet_id') or 'n/a'}",
                        f"Workspace: {sandbox_path}",
                        f"Changed files: {len(changed_files)}",
                        f"Applied to main project: {'yes' if applied_files else 'no'}",
                        f"Merge ready: {'yes' if merge_ready else 'no'}",
                    ],
                },
            },
            {
                "type": "execution_packet",
                "payload": {
                    **packet,
                    "sandbox_status": status,
                    "sandbox_branch": branch_label,
                    "sandbox_generated_at": generated_at,
                    "sandbox_path": str(sandbox_path),
                    "merge_ready": merge_ready,
                    "export_artifact": export_artifact,
                    "export_summary": export_summary,
                    "ready": True,
                    "merge_summary": (
                        "Verification passed in the isolated environment and the resulting files were applied to the main project."
                        if applied_files
                        else "The isolated run is complete. Review before merging or applying changes."
                    ),
                },
            },
            {
                "type": "plan_result",
                "payload": {
                    "title": "Sandbox execution plan",
                    "status": status,
                    "steps": execution_steps[:20],
                },
            },
        ]
        if approval_request:
            blocks.append(
                {
                    "type": "approval_request",
                    "payload": approval_request,
                }
            )
        if export_artifact:
            blocks.append(
                {
                    "type": "file_result",
                    "payload": {
                        "title": "Sandbox export",
                        "files": [
                            {
                                "title": export_artifact.get("title", "Sandbox ZIP"),
                                "summary": (export_summary or {}).get("description", "Download the generated output as a ZIP archive."),
                                "artifact_id": export_artifact.get("id"),
                            }
                        ],
                    },
                }
            )
        if changed_files:
            blocks.append(
                {
                    "type": "file_result",
                    "payload": {
                        "title": "Sandbox file changes",
                        "files": changed_files,
                    },
                }
            )
        if applied_files:
            blocks.append(
                {
                    "type": "file_result",
                    "payload": {
                        "title": "Applied files",
                        "files": [
                            {"path": path, "summary": "Applied back to the main project after successful isolated verification."}
                            for path in applied_files
                        ],
                    },
                }
            )
        return blocks
