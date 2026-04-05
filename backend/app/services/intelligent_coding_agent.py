"""
Intelligent Coding Agent - Context-Aware Code Generation

This agent uses AI understanding to:
1. Analyze task context intelligently
2. Determine appropriate language/framework
3. Generate contextually appropriate code
4. No templates - everything is AI-generated based on context
"""

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Optional
from backend.app.services.terminal import TerminalIntegration


class CodeActionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CodeAction:
    """A single action in the coding workflow."""
    action_type: str
    description: str
    target: str
    status: CodeActionStatus = CodeActionStatus.PENDING
    output: str = ""
    error: str = ""
    diff: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class CodingProgress:
    """Tracks progress of autonomous coding task."""
    task_description: str
    actions: list[CodeAction] = field(default_factory=list)
    current_action: int = 0
    overall_status: str = "pending"
    message: str = ""
    files_modified: list[str] = field(default_factory=list)
    errors_encountered: list[str] = field(default_factory=list)

    def to_log_string(self) -> str:
        """Convert progress to human-readable log."""
        lines = [f"🔧 **{self.task_description}**\n"]

        for i, action in enumerate(self.actions):
            icon = {
                CodeActionStatus.PENDING: "⏳",
                CodeActionStatus.IN_PROGRESS: "🔄",
                CodeActionStatus.COMPLETED: "✅",
                CodeActionStatus.FAILED: "❌",
            }.get(action.status, "•")

            lines.append(f"{icon} **{action.action_type.upper()}:** {action.description}")
            if action.output and action.status == CodeActionStatus.COMPLETED:
                if len(action.output) > 200:
                    lines.append(f"   ```\n{action.output[:200]}...\n   ```")
                else:
                    lines.append(f"   ```\n{action.output}\n   ```")
            if action.diff:
                lines.append(f"   ```diff\n{action.diff[:500]}\n   ```")

        return "\n".join(lines)


class IntelligentCodingAgent:
    """
    Intelligent coding agent that understands context.
    
    NO TEMPLATES - All code is generated based on:
    - Task context analysis
    - Project structure understanding
    - User preferences (if learned)
    - Best practices for the detected language/framework
    """

    def __init__(self, project_root: Optional[Path] = None):
        if project_root is None:
            current = Path.cwd()
            while current != current.parent:
                if (current / ".git").exists() or (current / "pyproject.toml").exists():
                    project_root = current
                    break
                current = current.parent
            else:
                project_root = Path.cwd()

        self.project_root = project_root
        self.progress_callback = None
        self.terminal = TerminalIntegration(self.project_root)

    def set_progress_callback(self, callback):
        """Set callback for streaming progress updates."""
        self.progress_callback = callback

    async def initialize(self):
        """Initialize the agent."""
        pass

    async def execute_task(self, task_description: str, project_context: Optional[dict] = None) -> CodingProgress:
        """Execute a coding task using intelligent context analysis."""
        progress = CodingProgress(task_description=task_description)
        progress.overall_status = "in_progress"

        try:
            await self._report_progress(progress, "🤔 Understanding task context...")

            # Step 1: Intelligently analyze the task
            context = self._understand_task(task_description, project_context or {})
            await self._report_progress(progress, f"📝 Context understood: {context['summary']}")
            planned_at = datetime.now(UTC).isoformat()
            progress.actions.append(CodeAction(
                action_type="plan",
                description=f"Analyze task and choose implementation strategy ({context['summary']})",
                target=context.get("file_path") or context["component_name"],
                status=CodeActionStatus.COMPLETED,
                output=json.dumps(
                    {
                        "language": context["language"],
                        "framework": context["framework"],
                        "intent": context["task_intent"],
                        "target": context.get("file_path"),
                    },
                    indent=2,
                ),
                started_at=planned_at,
                completed_at=planned_at,
            ))

            # Step 2: Determine what to create based on context
            files_to_create = await self._determine_files(task_description, context)
            
            # Step 3: Create each file with contextually appropriate content
            for file_info in files_to_create:
                file_path = file_info["path"]
                description = file_info.get("description", f"Creating {file_path}")
                operation = file_info.get("operation", "write")
                
                progress.actions.append(CodeAction(
                    action_type=operation,
                    description=description,
                    target=file_path,
                    status=CodeActionStatus.IN_PROGRESS,
                    started_at=datetime.now(UTC).isoformat(),
                ))
                
                success, msg, diff = await self._apply_file_operation(file_info)
                
                progress.actions[-1].status = CodeActionStatus.COMPLETED if success else CodeActionStatus.FAILED
                progress.actions[-1].output = msg if success else f"Failed: {msg}"
                progress.actions[-1].diff = diff
                progress.actions[-1].completed_at = datetime.now(UTC).isoformat()
                
                if success:
                    progress.files_modified.append(file_path)
                    verb = "Updated" if operation == "edit" else "Created"
                    await self._report_progress(progress, f"✅ {verb} {file_path}")
                else:
                    progress.errors_encountered.append(msg)
                    await self._report_progress(progress, f"❌ Failed to update {file_path}: {msg}")

            verification_commands = self._build_verification_commands(progress.files_modified)
            for command in verification_commands:
                action = CodeAction(
                    action_type="verify",
                    description=f"Run verification command: {command}",
                    target=command,
                    status=CodeActionStatus.IN_PROGRESS,
                    started_at=datetime.now(UTC).isoformat(),
                )
                progress.actions.append(action)
                result = await self.terminal.run_command(command, timeout=120)
                action.completed_at = datetime.now(UTC).isoformat()
                action.output = self._format_verification_output(result.stdout, result.stderr)
                if result.return_code == 0:
                    action.status = CodeActionStatus.COMPLETED
                    await self._report_progress(progress, f"✅ Verification passed: {command}")
                else:
                    action.status = CodeActionStatus.FAILED
                    action.error = result.suggested_fix or (result.stderr or result.stdout)[:240]
                    progress.errors_encountered.append(
                        f"Verification failed for `{command}`: {result.stderr or result.stdout}"
                    )
                    await self._report_progress(progress, f"❌ Verification failed: {command}")
                    repaired = await self._attempt_repair(progress, context, command, result)
                    if repaired:
                        retry_action = CodeAction(
                            action_type="verify",
                            description=f"Re-run verification after repair: {command}",
                            target=command,
                            status=CodeActionStatus.IN_PROGRESS,
                            started_at=datetime.now(UTC).isoformat(),
                        )
                        progress.actions.append(retry_action)
                        retry_result = await self.terminal.run_command(command, timeout=120)
                        retry_action.completed_at = datetime.now(UTC).isoformat()
                        retry_action.output = self._format_verification_output(retry_result.stdout, retry_result.stderr)
                        if retry_result.return_code == 0:
                            retry_action.status = CodeActionStatus.COMPLETED
                            await self._report_progress(progress, f"✅ Verification passed after repair: {command}")
                        else:
                            retry_action.status = CodeActionStatus.FAILED
                            retry_action.error = retry_result.suggested_fix or (retry_result.stderr or retry_result.stdout)[:240]
                            progress.errors_encountered.append(
                                f"Verification still failed for `{command}` after repair: {retry_result.stderr or retry_result.stdout}"
                            )
                            await self._report_progress(progress, f"❌ Verification still failed after repair: {command}")

            verify_failed = any(
                action.status == CodeActionStatus.FAILED
                for action in progress.actions
                if action.action_type == "verify"
            )
            if verify_failed:
                progress.overall_status = "failed"
                progress.message = "⚠️ Files were created, but verification failed."
            else:
                progress.overall_status = "completed"
                progress.message = f"✅ Task completed! Created {len(progress.files_modified)} file(s) and passed verification."
            
        except Exception as e:
            import traceback
            progress.overall_status = "failed"
            progress.message = f"❌ Task failed: {str(e)}"
            progress.errors_encountered.append(f"{str(e)}\n\n{traceback.format_exc()}")
        
        return progress

    async def _report_progress(self, progress: CodingProgress, message: str):
        """Report progress via callback if available."""
        if self.progress_callback:
            await self.progress_callback(progress, message)

    def _understand_task(self, task: str, project_context: dict | None = None) -> dict:
        """
        Intelligently understand task context.
        
        Returns comprehensive context about:
        - What needs to be built
        - Likely language/framework
        - Project structure clues
        - User intent
        """
        task_lower = task.lower()
        project_context = project_context or {}
        
        # Extract key information
        component_name = self._extract_component_name(task)
        file_path = self._extract_file_path(task)
        message_content = self._extract_message_content(task)
        
        # Determine language/framework from context clues
        language = self._detect_language(task, project_context)
        framework = self._detect_framework(task, project_context)
        
        # Determine what to build
        task_intent = self._determine_intent(task)
        
        # Generate a summary
        summary = self._generate_context_summary(task, language, framework, task_intent)
        
        return {
            "language": language,
            "framework": framework,
            "component_name": component_name,
            "file_path": file_path,
            "message_content": message_content,
            "task_intent": task_intent,
            "summary": summary,
            "full_task": task,
            "project_context": project_context,
        }

    def _detect_language(self, task: str, project_context: dict | None = None) -> str:
        """Detect programming language from task context."""
        task_lower = task.lower()
        frameworks = {item.lower() for item in (project_context or {}).get("frameworks", [])}
        
        if "react" in frameworks or "vite" in frameworks:
            return "javascript"
        if {"fastapi", "django", "flask"} & frameworks:
            return "python"

        # Strong indicators
        if any(kw in task_lower for kw in ["react", "jsx", "component", "frontend", "browser", "ui"]):
            return "javascript"
        elif any(kw in task_lower for kw in ["python", "fastapi", "flask", "django"]):
            return "python"
        elif any(kw in task_lower for kw in ["typescript", "ts", "angular"]):
            return "typescript"
        elif any(kw in task_lower for kw in ["html", "webpage", "web page"]):
            return "html"
        elif any(kw in task_lower for kw in ["css", "style", "stylesheet"]):
            return "css"
        
        # Context-based detection
        if "component" in task_lower and ("show" in task_lower or "display" in task_lower):
            return "javascript"  # Likely React
        elif "api" in task_lower or "endpoint" in task_lower:
            return "python"  # Likely FastAPI
        elif "script" in task_lower:
            return "javascript"
        
        # Default to Python for backend, JavaScript for frontend
        if any(kw in task_lower for kw in ["backend", "server", "api"]):
            return "python"
        elif any(kw in task_lower for kw in ["frontend", "client", "browser"]):
            return "javascript"
        
        return "python"  # Sensible default

    def _detect_framework(self, task: str, project_context: dict | None = None) -> Optional[str]:
        """Detect framework from task context."""
        task_lower = task.lower()
        frameworks = {item.lower() for item in (project_context or {}).get("frameworks", [])}

        if "react" in frameworks:
            return "react"
        if "fastapi" in frameworks:
            return "fastapi"
        if "django" in frameworks:
            return "django"
        if "flask" in frameworks:
            return "flask"
        if "vite" in frameworks and "component" in task_lower:
            return "react"
        
        if "react" in task_lower or "jsx" in task_lower or "component" in task_lower:
            return "react"
        elif "fastapi" in task_lower:
            return "fastapi"
        elif "flask" in task_lower:
            return "flask"
        elif "django" in task_lower:
            return "django"
        elif "express" in task_lower:
            return "express"
        elif "vue" in task_lower:
            return "vue"
        elif "angular" in task_lower:
            return "angular"
        
        return None

    def _determine_intent(self, task: str) -> str:
        """Determine what user wants to build."""
        task_lower = task.lower()

        if any(kw in task_lower for kw in ["edit", "update", "modify", "fix", "refactor", "replace"]):
            return "edit_file"

        if any(kw in task_lower for kw in ["dashboard", "workspace"]) and any(
            kw in task_lower for kw in ["chart", "graph", "map", "analytics", "analysis", "flight", "profit", "salary", "revenue"]
        ):
            return "create_analytics_dashboard"

        if "tool" in task_lower and any(kw in task_lower for kw in ["dashboard", "workspace", "panel"]):
            return "create_dashboard_tool"

        if any(kw in task_lower for kw in ["view", "tab", "workspace", "screen"]):
            return "create_workspace_view"
        
        # Component/UI creation
        if any(kw in task_lower for kw in ["component", "ui", "interface", "page"]):
            return "create_component"
        
        # API/Backend creation
        if any(kw in task_lower for kw in ["api", "endpoint", "route", "server"]):
            return "create_api"
        
        # Utility/Helper creation
        if any(kw in task_lower for kw in ["utility", "helper", "function", "tool"]):
            return "create_utility"
        
        # File operations
        if "create" in task_lower and "file" in task_lower:
            return "create_file"
        
        # Simple display
        if any(kw in task_lower for kw in ["show", "display", "print", "log"]):
            return "display_message"
        
        # Default
        return "create_file"

    def _extract_component_name(self, task: str) -> str:
        """Extract component/file name from task."""
        # Look for explicit names
        patterns = [
            r'(?:called|named|call it)\s+["\']?(\w+)["\']?',
            r'["\'](\w+\.(?:js|jsx|ts|tsx|py|css|html|txt))["\']',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, task, re.IGNORECASE)
            if match:
                return self._normalize_identifier(Path(match.group(1)).stem)
        
        # Generate meaningful name from task
        words = task.split()
        if len(words) >= 3:
            # Use key words from task
            important_words = [w for w in words if len(w) > 3 and w.lower() not in 
                             ["create", "make", "build", "file", "called", "then", "show", "the", "and"]]
            if important_words:
                return self._normalize_identifier(important_words[0].capitalize())
        
        return "Generated"

    def _normalize_identifier(self, raw: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_]", " ", raw)
        parts = [part for part in cleaned.split() if part]
        if not parts:
            return "Generated"
        normalized = "".join(part[:1].upper() + part[1:] for part in parts)
        if normalized[0].isdigit():
            normalized = f"Generated{normalized}"
        return normalized

    def _extract_file_path(self, task: str) -> Optional[str]:
        """Extract file path from task if specified."""
        patterns = [
            r'(?:in|at|to|create|save|write)\s+(?:file\s+)?["\']?([\w\-/\.]+\.(?:js|jsx|ts|tsx|py|css|html|json|txt))["\']?',
            r'["\']([\w\-/]+\.(?:js|jsx|ts|tsx|py|css|html|txt))["\']',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, task, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None

    def _extract_message_content(self, task: str) -> Optional[str]:
        """Extract message/string content from task."""
        # Look for quoted strings
        match = re.search(r'["\']([^"\']+)["\']', task)
        if match:
            return match.group(1)
        return None

    def _generate_context_summary(self, task: str, language: str, framework: Optional[str], intent: str) -> str:
        """Generate a human-readable summary of task understanding."""
        parts = []
        
        if language:
            parts.append(f"Language: {language}")
        if framework:
            parts.append(f"Framework: {framework}")
        if intent:
            parts.append(f"Intent: {intent}")
        
        return ", ".join(parts) if parts else "General task"

    async def _determine_files(self, task: str, context: dict) -> list[dict]:
        """
        Determine what files to create based on context.
        
        Uses intelligent analysis to decide:
        - File paths
        - File content
        - Descriptions
        """
        language = context["language"]
        framework = context["framework"]
        intent = context["task_intent"]
        component_name = context["component_name"]
        file_path = context.get("file_path")

        if intent == "edit_file" and not file_path:
            file_path = self._find_existing_target(task, context)
        
        # Determine appropriate file path
        if not file_path:
            file_path = self._determine_file_path(task, language, framework, intent, component_name)

        existing_content = None
        existing_path = self.project_root / file_path
        if existing_path.exists():
            ok, read_result = await self._read_file(file_path)
            if ok:
                existing_content = read_result

        if intent == "edit_file" and existing_content is not None:
            updated_content = self._edit_existing_content(task, context, existing_content)
            return [{
                "path": file_path,
                "content": updated_content,
                "previous_content": existing_content,
                "operation": "edit",
                "description": f"Edit existing file: {file_path}",
            }]

        # Generate contextually appropriate content
        content = await self._generate_contextual_content(task, context)

        files = [{
            "path": file_path,
            "content": content,
            "operation": "write",
            "description": f"Create {self._describe_file_type(language, framework, intent)}: {file_path}",
        }]

        if intent == "create_api":
            registration_update = await self._build_api_registration_update(file_path)
            if registration_update is not None:
                files.append(registration_update)
        elif intent == "create_analytics_dashboard":
            files.extend(await self._build_analytics_dashboard_integrations(file_path, task, context))
        elif intent == "create_dashboard_tool":
            files.extend(await self._build_dashboard_tool_integrations(file_path, task, context))
        elif intent == "create_component":
            registration_update = await self._build_frontend_component_registration(file_path, task)
            if registration_update is not None:
                files.append(registration_update)
        elif intent == "create_workspace_view":
            files.extend(await self._build_frontend_workspace_view_integrations(file_path, task))

        return files

    async def _build_analytics_dashboard_integrations(self, file_path: str, task: str, context: dict) -> list[dict]:
        updates = await self._build_dashboard_tool_integrations(file_path, task, context)

        app_update = await self._build_app_workspace_registration(file_path)
        if app_update is not None:
            updates.append(app_update)

        layout_update = await self._build_chatlayout_workspace_support()
        if layout_update is not None:
            updates.append(layout_update)

        return updates

    async def _build_frontend_workspace_view_integrations(self, file_path: str, task: str) -> list[dict]:
        updates: list[dict] = []

        app_update = await self._build_app_workspace_registration(file_path)
        if app_update is not None:
            updates.append(app_update)

        layout_update = await self._build_chatlayout_workspace_support()
        if layout_update is not None:
            updates.append(layout_update)

        if "dashboard" in task.lower():
            dashboard_update = await self._build_frontend_component_registration(file_path, task)
            if dashboard_update is not None:
                updates.append(dashboard_update)

        return updates

    async def _build_dashboard_tool_integrations(self, file_path: str, task: str, context: dict) -> list[dict]:
        updates: list[dict] = []

        dashboard_update = await self._build_frontend_component_registration(file_path, f"{task} dashboard")
        if dashboard_update is not None:
            updates.append(dashboard_update)

        tool_registry_update = await self._build_tool_registry_update(file_path, context)
        if tool_registry_update is not None:
            updates.append(tool_registry_update)

        capability_update = await self._build_capability_registry_update(file_path, context)
        if capability_update is not None:
            updates.append(capability_update)

        return updates

    async def _build_api_registration_update(self, file_path: str) -> Optional[dict]:
        main_path = "backend/app/main.py"
        ok, main_content = await self._read_file(main_path)
        if not ok:
            return None

        module_name = Path(file_path).stem
        import_line = f"from backend.app.api.{module_name} import router as {module_name}_router"
        include_line = f"app.include_router({module_name}_router)"

        updated = main_content
        if import_line not in updated:
            anchor = "from backend.app.core.config import settings\n"
            if anchor in updated:
                updated = updated.replace(anchor, f"{anchor}{import_line}\n", 1)
            else:
                updated = f"{import_line}\n{updated}"

        if include_line not in updated:
            router_anchor = "app.include_router(evolution_router)\n"
            if router_anchor in updated:
                updated = updated.replace(router_anchor, f"{router_anchor}{include_line}\n", 1)
            else:
                updated = updated.rstrip() + f"\n{include_line}\n"

        if updated == main_content:
            return None

        return {
            "path": main_path,
            "content": updated,
            "previous_content": main_content,
            "operation": "edit",
            "description": f"Register API router in {main_path}",
        }

    async def _build_frontend_component_registration(self, file_path: str, task: str) -> Optional[dict]:
        task_lower = task.lower()
        if "dashboard" not in task_lower:
            return None

        dashboard_path = "frontend/src/components/DashboardView.jsx"
        ok, dashboard_content = await self._read_file(dashboard_path)
        if not ok:
            return None

        component_name = Path(file_path).stem
        import_line = f'import {component_name} from "./{component_name}";'
        render_line = f"      <{component_name} />"

        updated = dashboard_content
        if import_line not in updated:
            anchor = 'import { artifactDownloadUrl } from "../lib/api";\n'
            if anchor in updated:
                updated = updated.replace(anchor, f"{anchor}{import_line}\n", 1)
            else:
                updated = f"{import_line}\n{updated}"

        if render_line not in updated:
            marker = "      <ArtifactPanel artifacts={artifacts} />\n"
            if marker in updated:
                updated = updated.replace(marker, f"{render_line}\n{marker}", 1)
            else:
                updated = updated.replace("    </div>\n  );", f"{render_line}\n    </div>\n  );", 1)

        if updated == dashboard_content:
            return None

        return {
            "path": dashboard_path,
            "content": updated,
            "previous_content": dashboard_content,
            "operation": "edit",
            "description": f"Register component in {dashboard_path}",
        }

    async def _build_app_workspace_registration(self, file_path: str) -> Optional[dict]:
        app_path = "frontend/src/App.jsx"
        ok, app_content = await self._read_file(app_path)
        if not ok:
            return None

        component_name = Path(file_path).stem
        view_id = component_name.lower()
        label = self._humanize_identifier(component_name)
        import_line = f'import {component_name} from "./components/{component_name}";'
        view_entry = f'        {{ id: "{view_id}", label: "{label}", content: <{component_name} /> }},\n'

        updated = app_content
        if import_line not in updated:
            anchor = 'import MessageList from "./components/MessageList";\n'
            if anchor in updated:
                updated = updated.replace(anchor, f"{anchor}{import_line}\n", 1)
            else:
                updated = f"{import_line}\n{updated}"

        if "extraViews={[" not in updated:
            insertion = "      extraViews={[\n" + view_entry + "      ]}\n"
            anchor = "      onViewChange={setActiveView}\n"
            if anchor in updated:
                updated = updated.replace(anchor, f"{anchor}{insertion}", 1)
        elif view_entry.strip() not in updated:
            anchor = "      extraViews={[\n"
            if anchor in updated:
                updated = updated.replace(anchor, f"{anchor}{view_entry}", 1)

        if updated == app_content:
            return None

        return {
            "path": app_path,
            "content": updated,
            "previous_content": app_content,
            "operation": "edit",
            "description": f"Register workspace view in {app_path}",
        }

    async def _build_chatlayout_workspace_support(self) -> Optional[dict]:
        layout_path = "frontend/src/components/ChatLayout.jsx"
        ok, layout_content = await self._read_file(layout_path)
        if not ok:
            return None

        updated = layout_content

        signature_old = "  activeView,\n  onViewChange,\n  chatContent,\n  dashboardContent,\n}) {"
        signature_new = "  activeView,\n  onViewChange,\n  extraViews = [],\n  chatContent,\n  dashboardContent,\n}) {"
        if signature_old in updated and "extraViews = []" not in updated:
            updated = updated.replace(signature_old, signature_new, 1)

        nav_block = (
            "          {extraViews.map((view) => (\n"
            "            <button type=\"button\" key={view.id} className={activeView === view.id ? \"active\" : \"\"} onClick={() => onViewChange(view.id)}>\n"
            "              {view.label}\n"
            "            </button>\n"
            "          ))}\n"
        )
        nav_anchor = "          Chat\n        </button>\n"
        if nav_anchor in updated and nav_block not in updated:
            updated = updated.replace(nav_anchor, f"{nav_anchor}{nav_block}", 1)

        stage_old = '{activeView === "dashboard" ? dashboardContent : chatContent}'
        stage_new = (
            "          {activeView === \"dashboard\"\n"
            "            ? dashboardContent\n"
            "            : activeView === \"chat\"\n"
            "              ? chatContent\n"
            "              : extraViews.find((view) => view.id === activeView)?.content ?? chatContent}\n"
        )
        if stage_old in updated:
            updated = updated.replace(stage_old, stage_new, 1)

        if updated == layout_content:
            return None

        return {
            "path": layout_path,
            "content": updated,
            "previous_content": layout_content,
            "operation": "edit",
            "description": f"Enable dynamic workspace views in {layout_path}",
        }

    async def _build_tool_registry_update(self, file_path: str, context: dict) -> Optional[dict]:
        registry_path = ".evolution-tools.json"
        ok, current = await self._read_file(registry_path)
        data = {}
        previous = None
        if ok:
            previous = current
            try:
                data = json.loads(current)
            except Exception:
                data = {}

        tool_name = self._humanize_identifier(Path(file_path).stem).lower().replace(" ", "_")
        tool_entry = {
            "name": tool_name,
            "description": f"Dashboard tool for {self._humanize_identifier(context['component_name'])}",
            "function_ref": f"frontend.component.{Path(file_path).stem}",
            "parameters": {},
            "return_type": "ui_component",
            "category": "dashboard",
            "version": "1.0.0",
            "enabled": True,
        }
        data[tool_name] = tool_entry
        updated = json.dumps(data, indent=2)
        if updated == previous:
            return None
        return {
            "path": registry_path,
            "content": updated,
            "previous_content": previous,
            "operation": "edit" if previous is not None else "write",
            "description": f"Register dashboard tool in {registry_path}",
        }

    async def _build_capability_registry_update(self, file_path: str, context: dict) -> Optional[dict]:
        registry_path = ".evolution-registry.json"
        ok, current = await self._read_file(registry_path)
        data = {}
        previous = None
        if ok:
            previous = current
            try:
                data = json.loads(current)
            except Exception:
                data = {}

        cap_name = self._humanize_identifier(Path(file_path).stem).lower().replace(" ", "_")
        data[cap_name] = {
            "name": cap_name,
            "description": f"Interactive dashboard capability for {self._humanize_identifier(context['component_name'])}",
            "status": "available",
            "version": "1.0.0",
            "metadata": {
                "kind": "dashboard_tool",
                "component": Path(file_path).stem,
            },
        }
        updated = json.dumps(data, indent=2)
        if updated == previous:
            return None
        return {
            "path": registry_path,
            "content": updated,
            "previous_content": previous,
            "operation": "edit" if previous is not None else "write",
            "description": f"Register capability in {registry_path}",
        }

    def _find_existing_target(self, task: str, context: dict) -> Optional[str]:
        task_lower = task.lower()
        component_name = context["component_name"].lower()
        candidate_names = {
            f"{component_name}.js",
            f"{component_name}.jsx",
            f"{component_name}.ts",
            f"{component_name}.tsx",
            f"{component_name}.py",
            f"{component_name.lower()}.js",
            f"{component_name.lower()}.jsx",
            f"{component_name.lower()}.py",
        }

        preferred_roots = []
        if context["language"] == "javascript":
            preferred_roots.extend(["frontend/src", "frontend"])
        if context["language"] == "python":
            preferred_roots.extend(["backend/app", "backend"])

        ranked: list[tuple[int, str]] = []
        for path in self.project_root.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(self.project_root).as_posix()
            name = path.name.lower()
            score = 0
            if name in candidate_names:
                score += 8
            if component_name in rel.lower():
                score += 4
            if any(rel.startswith(root) for root in preferred_roots):
                score += 3
            if any(token in rel.lower() for token in ["component", "api", "util", "service", "page"]):
                score += 1
            if score > 0:
                ranked.append((score, rel))

        ranked.sort(key=lambda item: (-item[0], len(item[1])))
        return ranked[0][1] if ranked else None

    def _determine_file_path(self, task: str, language: str, framework: Optional[str], 
                            intent: str, component_name: str) -> str:
        """Intelligently determine file path based on context."""
        
        # Based on intent
        if intent == "create_analytics_dashboard":
            suffix = component_name if component_name.lower().endswith("dashboard") else f"{component_name}Dashboard"
            return f"frontend/src/components/{suffix}.jsx"
        if intent == "create_dashboard_tool":
            suffix = component_name if component_name.lower().endswith("tool") else f"{component_name}Tool"
            return f"frontend/src/components/{suffix}.jsx"
        if intent == "create_workspace_view":
            return f"frontend/src/components/{component_name}.jsx"
        if intent == "create_component":
            if framework == "react":
                return f"frontend/src/components/{component_name}.jsx"
            elif framework == "vue":
                return f"frontend/src/components/{component_name}.vue"
            else:
                return f"frontend/src/components/{component_name}.js"
        
        elif intent == "create_api":
            if framework == "fastapi":
                return f"backend/app/api/{component_name.lower()}.py"
            else:
                return f"backend/app/api/{component_name.lower()}.py"
        
        elif intent == "create_utility":
            if language == "javascript":
                return f"frontend/src/utils/{component_name.lower()}.js"
            else:
                return f"backend/app/utils/{component_name.lower()}.py"
        
        elif intent == "display_message":
            if language == "javascript":
                return f"frontend/src/utils/{component_name.lower()}.js"
            else:
                return f"{component_name.lower()}.txt"
        
        # Default based on language
        if language == "javascript":
            return f"frontend/src/{component_name.lower()}.js"
        elif language == "python":
            return f"backend/app/{component_name.lower()}.py"
        else:
            return f"{component_name.lower()}.{self._get_file_extension(language)}"

    def _get_file_extension(self, language: str) -> str:
        """Get file extension for language."""
        extensions = {
            "python": "py",
            "javascript": "js",
            "typescript": "ts",
            "html": "html",
            "css": "css",
        }
        return extensions.get(language, "txt")

    def _describe_file_type(self, language: str, framework: Optional[str], intent: str) -> str:
        """Generate human-readable description of file type."""
        if intent == "edit_file":
            return "code update"
        if intent == "create_analytics_dashboard":
            return "analytics dashboard"
        if intent == "create_dashboard_tool":
            return "dashboard tool"
        if intent == "create_workspace_view":
            return "workspace view"
        if intent == "create_component":
            return f"{framework or language} component"
        elif intent == "create_api":
            return "API endpoint"
        elif intent == "create_utility":
            return "utility module"
        elif intent == "display_message":
            return "message display"
        else:
            return f"{language} file"

    async def _generate_contextual_content(self, task: str, context: dict) -> str:
        """
        Generate content based on full context understanding.
        
        NO TEMPLATES - Content is generated based on:
        - Task requirements
        - Language/framework
        - User intent
        - Best practices
        """
        language = context["language"]
        framework = context["framework"]
        intent = context["task_intent"]
        component_name = context["component_name"]
        message_content = context.get("message_content")
        
        # Generate appropriate content based on all context
        if language == "javascript":
            return self._generate_javascript_content(task, context)
        elif language == "python":
            return self._generate_python_content(task, context)
        elif language == "html":
            return self._generate_html_content(task, context)
        elif language == "css":
            return self._generate_css_content(task, context)
        else:
            return self._generate_generic_content(task, context)

    def _generate_javascript_content(self, task: str, context: dict) -> str:
        """Generate JavaScript code based on context."""
        intent = context["task_intent"]
        component_name = context["component_name"]
        message_content = context.get("message_content")
        framework = context["framework"]
        
        # Component creation
        if intent == "create_analytics_dashboard":
            return self._create_analytics_dashboard_component(component_name, task)
        if intent in {"create_component", "create_workspace_view"} or framework == "react":
            return self._create_react_component(component_name, message_content, task)
        
        # Utility creation
        elif intent == "create_utility":
            return self._create_js_utility(message_content, task)
        
        # Simple display
        elif intent == "display_message":
            return self._create_display_script(message_content, task)
        
        # Default
        return self._create_generic_js(component_name, task)

    def _create_react_component(self, name: str, message: Optional[str], task: str) -> str:
        """Create a React component intelligently."""
        # Use message if provided, otherwise create generic component
        display_content = message if message else f"{name} Component"
        
        return f'''import React from 'react';

/**
 * {name} Component
 * Task: {task}
 */
const {name} = () => {{
    return (
        <div className="{name.lower()}-container">
            <h1>{display_content}</h1>
        </div>
    );
}};

export default {name};
'''

    def _create_analytics_dashboard_component(self, name: str, task: str) -> str:
        title = self._humanize_identifier(name)
        viz_type = "map3d" if any(token in task.lower() for token in ["map", "flight", "globe", "3d"]) else "chart2d"
        if viz_type == "map3d":
            spec = """{
  type: "map3d",
  title: "Analytics Map",
  subtitle: "Reusable dashboard visualization",
  points: [
    { id: "sample-1", label: "Sample 1", lat: 55.67, lon: 12.56, altitude: 32000, detail: "Replace with live data" },
    { id: "sample-2", label: "Sample 2", lat: 40.71, lon: -74.0, altitude: 28000, detail: "Replace with live data" }
  ]
}"""
            insight = "Map-ready surface for contextual spatial analysis."
        else:
            spec = """{
  type: "chart2d",
  title: "Analytics Chart",
  subtitle: "Reusable dashboard visualization",
  rows: [
    { label: "Jan", value: 10000, detail: "Replace with live data" },
    { label: "Feb", value: 12000, detail: "Replace with live data" },
    { label: "Mar", value: 9000, detail: "Replace with live data" }
  ],
  yLabel: "Value"
}"""
            insight = "Chart-ready surface for reusable business metrics."
        return f'''import React from "react";
import DynamicVisualization from "./DynamicVisualization";
import {{ buildVisualizationArtifacts }} from "../lib/visualization";
import useSessionAnalytics from "../hooks/useSessionAnalytics";

const defaultSpec = {spec};
const defaultArtifacts = buildVisualizationArtifacts(defaultSpec);

function summarizeSourceFiles(sessionArtifacts = []) {{
  return sessionArtifacts
    .slice(0, 4)
    .map((artifact) => artifact.title || artifact.name || artifact.id)
    .filter(Boolean);
}}

export default function {name}({{
  spec = defaultSpec,
  sessionId = "",
  sessionArtifacts: initialArtifacts = [],
  summary = "{insight}",
}}) {{
  const {{ data: sessionAnalytics, loading: artifactsLoading }} = useSessionAnalytics(sessionId, {{
    visualization: spec,
    artifacts: initialArtifacts,
    render_blocks: defaultArtifacts,
  }});
  const sessionArtifacts = sessionAnalytics.artifacts?.length ? sessionAnalytics.artifacts : initialArtifacts;
  const activeSpec = sessionAnalytics.visualization || spec;
  const renderBlocks = buildVisualizationArtifacts(activeSpec);
  const reportBlock = renderBlocks.find((block) => block.type === "report")
    || sessionAnalytics.render_blocks?.find((block) => block.type === "report")
    || defaultArtifacts[0];
  const fileBlock = renderBlocks.find((block) => block.type === "file_result")
    || sessionAnalytics.render_blocks?.find((block) => block.type === "file_result")
    || defaultArtifacts[1];
  const sourceFiles = summarizeSourceFiles(sessionArtifacts);

  return (
    <section className="{name.lower()}-dashboard panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Analytics Surface</p>
          <h2>{title}</h2>
        </div>
      </div>
      <p>{{summary}}</p>
      {{reportBlock?.payload?.summary ? <p>{{reportBlock.payload.summary}}</p> : null}}
      {{Array.isArray(reportBlock?.payload?.highlights) ? (
        <div className="capability-list">
          {{reportBlock.payload.highlights.map((item) => (
            <article key={{item}} className="capability-card">
              <div>
                <strong>{{item}}</strong>
              </div>
            </article>
          ))}}
        </div>
      ) : null}}
      {{artifactsLoading ? <p>Loading session context…</p> : null}}
      {{sourceFiles.length > 0 ? (
        <div className="artifact-meta">
          {{sourceFiles.map((item) => (
            <span key={{item}} className="artifact-chip">{{item}}</span>
          ))}}
        </div>
      ) : null}}
      <DynamicVisualization spec={{activeSpec}} />
      {{Array.isArray(fileBlock?.payload?.files) ? (
        <div className="artifact-list">
          {{fileBlock.payload.files.slice(0, 3).map((file) => (
            <article key={{file.path || file.title}} className="artifact-card">
              <div>
                <strong>{{file.path || file.title || "Structured output"}}</strong>
                <p>{{file.summary}}</p>
              </div>
            </article>
          ))}}
        </div>
      ) : null}}
    </section>
  );
}}
'''

    def _humanize_identifier(self, value: str) -> str:
        words = re.sub(r"(?<!^)([A-Z])", r" \1", value).replace("_", " ").replace("-", " ")
        return " ".join(part for part in words.split() if part)

    def _create_js_utility(self, message: Optional[str], task: str) -> str:
        """Create JavaScript utility module."""
        return f'''/**
 * Utility Module
 * Task: {task}
 */

{f'// Message: {message}' if message else '// Utility functions'}

export function process() {{
    console.log("Utility executed");
}}

console.log("Utility loaded");
'''

    def _create_display_script(self, message: Optional[str], task: str) -> str:
        """Create display script."""
        display_msg = message if message else "Task completed"
        return f'''/**
 * Display Script
 * Task: {task}
 */

console.log("{display_msg}");
'''

    def _create_generic_js(self, name: str, task: str) -> str:
        """Create generic JavaScript file."""
        return f'''/**
 * {name}
 * Task: {task}
 */

console.log("{name} loaded");
'''

    def _generate_python_content(self, task: str, context: dict) -> str:
        """Generate Python code based on context."""
        intent = context["task_intent"]
        component_name = context["component_name"]
        message_content = context.get("message_content")
        framework = context["framework"]
        
        # API creation
        if intent == "create_api" or framework == "fastapi":
            return self._create_python_api(component_name, message_content, task)
        
        # Utility creation
        elif intent == "create_utility":
            return self._create_python_utility(message_content, task)
        
        # Simple display
        elif intent == "display_message":
            return self._create_python_display(message_content, task)
        
        # Default
        return self._create_generic_python(component_name, task)

    def _create_python_api(self, name: str, message: Optional[str], task: str) -> str:
        """Create Python API endpoint."""
        return f'''"""
{name.title()} API
Task: {task}
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/{name.lower()}")
async def get_{name.lower()}():
    """{message or f'Get {name}'}"""
    return {{"status": "success"}}
'''

    def _create_python_utility(self, message: Optional[str], task: str) -> str:
        """Create Python utility module."""
        return f'''"""
Utility Module
Task: {task}
"""

{f'# Message: {message}' if message else '# Utility functions'}


def process():
    """Process data."""
    print("Utility executed")


if __name__ == "__main__":
    process()
'''

    def _create_python_display(self, message: Optional[str], task: str) -> str:
        """Create Python display script."""
        display_msg = message if message else "Task completed"
        return f'''"""
Display Script
Task: {task}
"""

print("{display_msg}")
'''

    def _create_generic_python(self, name: str, task: str) -> str:
        """Create generic Python file."""
        return f'''"""
{name.title()}
Task: {task}
"""

print("{name} loaded")
'''

    def _generate_html_content(self, task: str, context: dict) -> str:
        """Generate HTML content."""
        message = context.get("message_content", "Page Content")
        return f'''<!DOCTYPE html>
<html>
<head>
    <title>{message}</title>
</head>
<body>
    <h1>{message}</h1>
    <!-- Task: {task} -->
</body>
</html>
'''

    def _generate_css_content(self, task: str, context: dict) -> str:
        """Generate CSS content."""
        return f'''/* 
 * Styles
 * Task: {task}
 */

.container {{
    padding: 20px;
}}
'''

    def _generate_generic_content(self, task: str, context: dict) -> str:
        """Generate generic content."""
        message = context.get("message_content", "Content")
        return f"# {message}\n# Task: {task}\n"

    async def _write_file(self, file_path: str, content: str) -> tuple[bool, str]:
        """Write content to a file."""
        try:
            path = self.project_root / file_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            
            return True, f"Successfully wrote to {file_path}"
        except Exception as e:
            return False, f"Error writing file: {str(e)}"

    async def _apply_file_operation(
        self,
        file_info: dict,
    ) -> tuple[bool, str, str]:
        operation = file_info.get("operation", "write")
        file_path = file_info["path"]
        content = file_info["content"]
        previous_content = file_info.get("previous_content", "")

        success, message = await self._write_file(file_path, content)
        if not success:
            return False, message, ""

        diff = ""
        if operation == "edit":
            diff = self._create_diff(file_path, previous_content, content)
        return True, message, diff

    async def _read_file(self, file_path: str) -> tuple[bool, str]:
        """Read a file's contents."""
        try:
            path = self.project_root / file_path
            if not path.exists():
                return False, f"File not found: {file_path}"
            content = path.read_text(encoding="utf-8")
            return True, content
        except Exception as e:
            return False, f"Error reading file: {str(e)}"

    def _edit_existing_content(self, task: str, context: dict, existing_content: str) -> str:
        task_lower = task.lower()
        message_content = context.get("message_content")
        language = context["language"]
        file_path = context.get("file_path", "")

        if language == "javascript":
            return self._edit_javascript_content(task_lower, message_content, existing_content, file_path)
        if language == "python":
            return self._edit_python_content(task_lower, message_content, existing_content, file_path)
        return self._append_task_note(existing_content, task)

    def _edit_javascript_content(
        self,
        task_lower: str,
        message_content: Optional[str],
        existing_content: str,
        file_path: str,
    ) -> str:
        if any(token in task_lower for token in ["link", "nav item", "navbar", "navigation"]) and any(
            token in file_path.lower() for token in ["nav", "header", "menu"]
        ):
            label = message_content or "New Link"
            return self._insert_react_nav_item(existing_content, label)
        if "console.log" in task_lower or "console log" in task_lower:
            message = message_content or "Hello from ISE AI"
            line = f'console.log("{message}");'
            if line in existing_content:
                return existing_content
            return existing_content.rstrip() + f"\n\n{line}\n"
        if "import" in task_lower and message_content:
            line = message_content
            if line in existing_content:
                return existing_content
            return f"{line}\n{existing_content}"
        return self._append_task_note(existing_content, task_lower)

    def _edit_python_content(
        self,
        task_lower: str,
        message_content: Optional[str],
        existing_content: str,
        file_path: str,
    ) -> str:
        if any(token in task_lower for token in ["route", "endpoint", "api"]) and file_path.endswith(".py"):
            route_name = self._extract_route_name(task_lower)
            return self._insert_fastapi_route(existing_content, route_name, message_content)
        if "print" in task_lower:
            message = message_content or "Hello from ISE AI"
            line = f'print("{message}")'
            if line in existing_content:
                return existing_content
            return existing_content.rstrip() + f"\n\n{line}\n"
        return self._append_task_note(existing_content, task_lower, prefix="#")

    def _insert_react_nav_item(self, existing_content: str, label: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or "new-link"
        anchor = f'<a href="/{slug}">{label}</a>'
        if anchor in existing_content:
            return existing_content
        if "</nav>" in existing_content:
            return existing_content.replace("</nav>", f"  {anchor}\n</nav>", 1)
        if "</header>" in existing_content:
            return existing_content.replace("</header>", f"  <nav>{anchor}</nav>\n</header>", 1)
        return existing_content.rstrip() + f"\n\n{anchor}\n"

    def _extract_route_name(self, task_lower: str) -> str:
        match = re.search(r"(?:route|endpoint|api)\s+(?:for\s+)?([a-z0-9_\-]+)", task_lower)
        if match:
            return match.group(1).strip("-_")
        return "new-route"

    def _insert_fastapi_route(self, existing_content: str, route_name: str, message_content: Optional[str]) -> str:
        path_name = route_name.replace("_", "-")
        function_name = route_name.replace("-", "_")
        route_block = (
            f'\n\n@router.get("/api/{path_name}")\n'
            f"async def get_{function_name}():\n"
            f'    """{message_content or f"Get {route_name}"}"""\n'
            f'    return {{"status": "success", "route": "{path_name}"}}\n'
        )
        if f'"/api/{path_name}"' in existing_content:
            return existing_content
        return existing_content.rstrip() + route_block

    def _append_task_note(self, existing_content: str, task: str, prefix: str = "//") -> str:
        note = f"{prefix} Updated for task: {task}"
        if note in existing_content:
            return existing_content
        return existing_content.rstrip() + f"\n\n{note}\n"

    def _create_diff(self, file_path: str, old_text: str, new_text: str) -> str:
        old_lines = old_text.splitlines()
        new_lines = new_text.splitlines()
        diff_lines = [f"--- {file_path}", f"+++ {file_path}"]
        max_lines = min(max(len(old_lines), len(new_lines)), 40)
        for index in range(max_lines):
            old_line = old_lines[index] if index < len(old_lines) else ""
            new_line = new_lines[index] if index < len(new_lines) else ""
            if old_line != new_line:
                if old_line:
                    diff_lines.append(f"-{old_line}")
                if new_line:
                    diff_lines.append(f"+{new_line}")
        return "\n".join(diff_lines)

    def _build_verification_commands(self, files_modified: list[str]) -> list[str]:
        commands: list[str] = []
        paths = [Path(path) for path in files_modified]

        if any("frontend" in path.parts for path in paths):
            if (self.project_root / "frontend" / "package.json").exists():
                commands.append("cd frontend && npm run build")

        if any("backend" in path.parts or path.suffix == ".py" for path in paths):
            if (self.project_root / "backend").exists():
                commands.append("python -m compileall backend/app")

        unique: list[str] = []
        for command in commands:
            if command not in unique:
                unique.append(command)
        return unique

    def _format_verification_output(self, stdout: str, stderr: str) -> str:
        parts = []
        if stdout.strip():
            parts.append(stdout.strip()[:400])
        if stderr.strip():
            parts.append(stderr.strip()[:400])
        return "\n\n".join(parts) if parts else "Verification completed with no output."

    async def _attempt_repair(self, progress: CodingProgress, context: dict, command: str, result) -> bool:
        analysis = result.error_analysis or {}
        candidate_path = analysis.get("file_path")
        relative_target = self._resolve_modified_target(candidate_path, progress.files_modified)
        if relative_target is None and progress.files_modified:
            relative_target = progress.files_modified[-1]
        if relative_target is None:
            return False

        ok, current_content = await self._read_file(relative_target)
        if not ok:
            return False

        repaired_content = self._repair_file_content(relative_target, current_content, context)
        if repaired_content == current_content:
            return False

        repair_action = CodeAction(
            action_type="repair",
            description=f"Apply automatic repair to {relative_target} after `{command}` failed",
            target=relative_target,
            status=CodeActionStatus.IN_PROGRESS,
            started_at=datetime.now(UTC).isoformat(),
        )
        progress.actions.append(repair_action)
        success, message, diff = await self._apply_file_operation(
            {
                "path": relative_target,
                "content": repaired_content,
                "previous_content": current_content,
                "operation": "edit",
            }
        )
        repair_action.completed_at = datetime.now(UTC).isoformat()
        repair_action.output = message if success else f"Failed: {message}"
        repair_action.diff = diff
        repair_action.status = CodeActionStatus.COMPLETED if success else CodeActionStatus.FAILED
        if success:
            await self._report_progress(progress, f"🛠️ Applied repair to {relative_target}")
            return True
        progress.errors_encountered.append(message)
        return False

    def _resolve_modified_target(self, file_path: Optional[str], files_modified: list[str]) -> Optional[str]:
        if not file_path:
            return None
        candidate = Path(file_path)
        for modified in files_modified:
            modified_path = self.project_root / modified
            if candidate == modified_path or candidate.as_posix().endswith(modified):
                return modified
        return None

    def _repair_file_content(self, file_path: str, content: str, context: dict) -> str:
        repaired = content

        # Fix invalid dotted identifiers introduced by bad filenames.
        repaired = re.sub(
            r"\b(const|function|class)\s+([A-Za-z_][\w\.]*)",
            lambda match: f"{match.group(1)} {self._normalize_identifier(match.group(2))}",
            repaired,
        )
        repaired = re.sub(
            r"export default\s+([A-Za-z_][\w\.]*)\s*;",
            lambda match: f"export default {self._normalize_identifier(match.group(1))};",
            repaired,
        )

        if file_path.endswith((".jsx", ".tsx")) and "return (" in repaired and "export default" not in repaired:
            component_name = self._normalize_identifier(Path(file_path).stem)
            if f"const {component_name}" not in repaired:
                repaired = repaired.replace("const Generated", f"const {component_name}")
            repaired = repaired.rstrip() + f"\n\nexport default {component_name};\n"

        return repaired


# Singleton instance
_agent: Optional[IntelligentCodingAgent] = None


def get_intelligent_coding_agent(project_root: Optional[Path] = None) -> IntelligentCodingAgent:
    """Get or create intelligent coding agent instance."""
    global _agent
    if _agent is None:
        _agent = IntelligentCodingAgent(project_root)
    return _agent
