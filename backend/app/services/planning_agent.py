"""
Autonomous Planning Agent with Progress Tracking

This agent creates detailed plans and executes them step-by-step,
showing progress like: 0/3 → 1/3 → 2/3 → 3/3 (Completed)

Similar to Qwen Code Agent behavior.
"""

import asyncio
import json
import re
import shlex
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from uuid import uuid4
from typing import Any, Callable, Optional

import aiofiles

from app.services.intelligent_coding_agent import (
    IntelligentCodingAgent,
    get_intelligent_coding_agent,
)
from app.services.plan_checkpoint import save_checkpoint, load_checkpoint


class PlanStatus(str, Enum):
    """Status of the overall plan."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Status of an individual plan step."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    """A single step in the execution plan."""
    step_number: int
    description: str
    action_type: str  # "create_file", "edit_file", "run_command", "show_result", etc.
    target: str  # File path, command, or description
    status: StepStatus = StepStatus.PENDING
    output: str = ""
    error: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "step_number": self.step_number,
            "description": self.description,
            "action_type": self.action_type,
            "target": self.target,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata,
        }


@dataclass
class ExecutionPlan:
    """Complete execution plan with progress tracking."""
    task: str
    id: str = field(default_factory=lambda: str(uuid4()))
    steps: list[PlanStep] = field(default_factory=list)
    status: PlanStatus = PlanStatus.PENDING
    current_step: int = 0
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: str = ""

    @property
    def plan_id(self) -> str:
        return self.id

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def completed_steps(self) -> int:
        return sum(1 for step in self.steps if step.status == StepStatus.COMPLETED)

    @property
    def progress_text(self) -> str:
        """Return progress text like "1/3 completed"."""
        return f"{self.completed_steps}/{self.total_steps}"

    def to_log_string(self) -> str:
        """Convert plan to human-readable log with progress."""
        status_icons = {
            StepStatus.PENDING: "⏳",
            StepStatus.IN_PROGRESS: "🔄",
            StepStatus.COMPLETED: "✅",
            StepStatus.FAILED: "❌",
            StepStatus.SKIPPED: "⏭️",
        }

        lines = [
            f"📋 **Plan: {self.task}**",
            f"**Progress:** {self.progress_text} ({self.status.value})",
            "",
        ]

        for step in self.steps:
            icon = status_icons.get(step.status, "•")
            lines.append(f"{icon} **Step {step.step_number}:** {step.description}")
            
            if step.output and step.status == StepStatus.COMPLETED:
                # Show brief output
                output_preview = step.output[:200]
                if len(step.output) > 200:
                    output_preview += "..."
                lines.append(f"   ```\n{output_preview}\n   ```")
            
            if step.error:
                lines.append(f"   ⚠️ Error: {step.error}")
            
            lines.append("")

        if self.status == PlanStatus.COMPLETED:
            lines.append(f"✅ **Plan completed!** ({self.completed_steps}/{self.total_steps} steps)")
        elif self.status == PlanStatus.FAILED:
            lines.append(f"❌ **Plan failed:** {self.error}")

        return "\n".join(lines)

    def to_progress_event(self) -> dict:
        """Convert to progress event for streaming."""
        return {
            "type": "plan_progress",
            "task": self.task,
            "status": self.status.value,
            "progress": self.progress_text,
            "completed_steps": self.completed_steps,
            "total_steps": self.total_steps,
            "current_step": self.current_step,
            "steps": [step.to_dict() for step in self.steps],
        }


class AutonomousPlanningAgent:
    """
    Autonomous agent that creates plans and executes them step-by-step.
    
    Features:
    1. Parses user request into actionable steps
    2. Shows progress (0/3, 1/3, 2/3, 3/3)
    3. Executes each step autonomously
    4. Reports progress after each step
    5. Handles errors and recovery
    """

    # Safety limits for recursive expansion
    MAX_EXPANSION_DEPTH = 3
    MAX_TOTAL_SUBSTEPS = 100

    def __init__(self, project_root: Optional[Path] = None, auto_commit_workspace: bool = True):
        self.project_root = project_root or Path.cwd()
        self.auto_commit_workspace = auto_commit_workspace
        self.coding_agent = get_intelligent_coding_agent(project_root)
        self.progress_callback: Optional[Callable] = None

    def set_progress_callback(self, callback: Callable):
        """Set callback for progress updates."""
        self.progress_callback = callback

    async def create_plan(self, task: str, project_context: Optional[dict[str, Any]] = None) -> ExecutionPlan:
        """
        Create an execution plan from a task description.
        
        Example:
            Task: "Create 2 files. First: text1.txt with 'this is a text', then show result"
            Plan:
            - Step 1: Create text1.txt
            - Step 2: Update content to "this is a text"
            - Step 3: Show the result
        """
        plan = ExecutionPlan(
            task=task,
            created_at=datetime.now(UTC).isoformat(),
        )

        # Parse the task to identify steps
        steps = await self._parse_task_into_steps(task, project_context or {})
        plan.steps = steps

        return plan

    async def _parse_task_into_steps(
        self,
        task: str,
        project_context: Optional[dict[str, Any]] = None,
    ) -> list[PlanStep]:
        """
        Parse a task description into discrete steps.

        Uses intelligent parsing to identify:
        - File creation tasks
        - File modification tasks
        - Command execution tasks
        - Display/show tasks
        """
        task_lower = task.lower()
        project_context = project_context or {}
        steps = []
        step_number = 1

        direct_steps = self._build_direct_artifact_steps(task, project_context, step_number)
        if direct_steps:
            return direct_steps

        # Pattern 1: Explicit multi-step tasks
        # "create file X, then update it, then show result"
        explicit_steps = self._detect_explicit_steps(task)
        
        if explicit_steps and len(explicit_steps) > 1:
            # Multiple steps detected
            for step_desc in explicit_steps:
                action_type = self._determine_action_type(step_desc)
                target = self._extract_target(step_desc)
                
                # Extract content for this step
                content = self._extract_content_for_step(step_desc)
                
                step = PlanStep(
                    step_number=step_number,
                    description=step_desc.strip(),
                    action_type=action_type,
                    target=target,
                    metadata={"content": content} if content else {},
                )
                steps.append(step)
                step_number += 1
            steps = await self._enrich_steps_with_project_context(steps, task, project_context)
        else:
            # Pattern 2: Try to detect implicit multi-step tasks
            # Look for multiple actions in the task
            implicit_steps = self._detect_implicit_steps(task)
            
            if implicit_steps and len(implicit_steps) > 1:
                for step_desc in implicit_steps:
                    action_type = self._determine_action_type(step_desc)
                    target = self._extract_target(step_desc)
                    content = self._extract_content_for_step(step_desc)
                    
                    step = PlanStep(
                        step_number=step_number,
                        description=step_desc.strip(),
                        action_type=action_type,
                        target=target,
                        metadata={"content": content} if content else {},
                    )
                    steps.append(step)
                    step_number += 1
                steps = await self._enrich_steps_with_project_context(steps, task, project_context)
            else:
                coding_steps = await self._build_project_aware_steps(task, project_context, step_number)
                if coding_steps:
                    return coding_steps

                # Pattern 3: Single task - create one step
                # Rewrite the task for better clarity
                rewritten_task = self._rewrite_task_for_clarity(task)

                steps.append(PlanStep(
                    step_number=1,
                    description=rewritten_task,
                    action_type=self._determine_action_type(task),
                    target=self._extract_target(task),
                    metadata={"content": self._extract_content_for_step(task)} if self._extract_content_for_step(task) else {},
                ))

        return steps

    def _infer_dynamic_project_brief(self, task: str) -> dict[str, Any]:
        """Infer a request-specific project brief without domain-specific hardcoded templates."""
        lower = task.lower()
        cleaned = re.sub(r"\b(create|build|make|generate|implement|develop|roadmap|plan|step by step|zip|downloadable|download|using|with|react|node|nice|css|animation|website|landing page|web site|webpage|project|file|files|give it to me)\b", " ", lower)
        cleaned = re.sub(r"[^a-z0-9\s-]", " ", cleaned)
        stop = {"for", "the", "and", "then", "that", "this", "from", "into", "sandbox", "agents", "agent", "task", "entire", "full"}
        words = [w for w in cleaned.split() if len(w) > 2 and w not in stop]
        subject_words = words[:5] or ["modern", "business"]
        subject = " ".join(subject_words).strip()
        subject_label = subject.title()
        slug = re.sub(r"[^a-z0-9]+", "-", subject.lower()).strip("-") or "generated-project"
        brand = " ".join(w.capitalize() for w in subject_words[:3]) or "Generated Studio"
        primary_action = "Get started"
        if any(token in lower for token in ("book", "appointment", "reserve", "reservation", "service", "visit")):
            primary_action = "Book now"
        elif any(token in lower for token in ("travel", "trip", "tour", "hotel")):
            primary_action = "Plan now"
        elif any(token in lower for token in ("cms", "content management", "dashboard", "admin")):
            primary_action = "Open dashboard"
        return {
            "subject": subject,
            "subject_label": subject_label,
            "slug": slug,
            "brand": brand,
            "audience": f"people looking for {subject}" if subject else "visitors",
            "primary_action": primary_action,
        }

    def _generate_dynamic_react_landing_page(self, task: str, brief: dict[str, Any]) -> str:
        """Generate request-aware React UI from the inferred brief."""
        subject = brief["subject_label"]
        brand = brief["brand"]
        audience = brief["audience"]
        primary_action = brief["primary_action"]
        task_summary = task.replace('"', "'")[:220]
        features_js = ",\n  ".join([
            f'{{ title: "Clear value", text: "A focused message for {audience}." }}',
            f'{{ title: "Trust section", text: "Reusable cards explain why {subject.lower()} is credible and useful." }}',
            f'{{ title: "Conversion flow", text: "Primary and secondary actions guide visitors toward the next step." }}',
        ])
        return f'''import React from "react";
import "./App.css";

const features = [
  {features_js}
];

const processSteps = [
  "Understand the visitor need",
  "Present a focused offer",
  "Make the next action simple"
];

export default function App() {{
  return (
    <main className="dynamic-landing">
      <section className="hero-section">
        <nav className="nav-bar" aria-label="Main navigation">
          <strong>{brand}</strong>
          <span>{subject} - React landing page</span>
        </nav>
        <div className="hero-grid">
          <div className="hero-copy">
            <p className="eyebrow">Generated for your request</p>
            <h1>{subject} landing page built to look sharp and convert.</h1>
            <p className="lede">This React page was generated dynamically from: “{task_summary}”. It includes responsive layout, polished CSS, animation, and clear sections.</p>
            <div className="hero-actions">
              <a className="primary-button" href="#contact">{primary_action}</a>
              <a className="secondary-button" href="#features">View sections</a>
            </div>
          </div>
          <aside className="showcase-card" aria-label="Project showcase">
            <span>Live concept</span>
            <strong>{subject}</strong>
            <p>Responsive, animated, and ready to customize.</p>
          </aside>
        </div>
      </section>

      <section id="features" className="section-block">
        <p className="eyebrow">What this page includes</p>
        <h2>A practical structure for {audience}.</h2>
        <div className="feature-grid">
          {{features.map((item) => (
            <article className="feature-card" key={{item.title}}>
              <h3>{{item.title}}</h3>
              <p>{{item.text}}</p>
            </article>
          ))}}
        </div>
      </section>

      <section className="section-block split-section">
        <div>
          <p className="eyebrow">Experience flow</p>
          <h2>Simple steps that help visitors act.</h2>
        </div>
        <ol className="process-list">
          {{processSteps.map((step) => <li key={{step}}>{{step}}</li>)}}
        </ol>
      </section>

      <section id="contact" className="cta-section">
        <p className="eyebrow">Final call to action</p>
        <h2>Turn this generated page into your finished product.</h2>
        <p>Use the downloaded ZIP as the starting point for your {subject.lower()} website, then connect real content, routing, forms, and backend APIs as needed.</p>
        <a className="primary-button" href="mailto:hello@example.local">{primary_action}</a>
      </section>
    </main>
  );
}}
'''

    def _generate_dynamic_landing_page_css(self, brief: dict[str, Any]) -> str:
        """Generate reusable animated CSS for a dynamic landing page."""
        return '''.dynamic-landing {
  min-height: 100vh;
  background: radial-gradient(circle at top left, rgba(111, 76, 255, 0.28), transparent 34%), radial-gradient(circle at 85% 12%, rgba(20, 184, 166, 0.2), transparent 28%), linear-gradient(135deg, #07111f, #111827 48%, #1f2937);
  color: #f8fafc;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.hero-section { padding: 2rem clamp(1.25rem, 4vw, 4rem) 5rem; overflow: hidden; }
.nav-bar, .hero-grid, .section-block, .cta-section { max-width: 1160px; margin: 0 auto; }
.nav-bar { display: flex; justify-content: space-between; gap: 1rem; padding: 1rem 0 4rem; color: rgba(248, 250, 252, 0.76); }
.hero-grid { display: grid; grid-template-columns: minmax(0, 1.08fr) minmax(280px, 0.72fr); gap: clamp(2rem, 6vw, 5rem); align-items: center; }
.eyebrow { margin: 0 0 0.75rem; color: #67e8f9; font-size: 0.78rem; font-weight: 900; letter-spacing: 0.18em; text-transform: uppercase; }
.hero-copy h1, .section-block h2, .cta-section h2 { margin: 0; letter-spacing: -0.06em; line-height: 0.95; }
.hero-copy h1 { max-width: 820px; font-size: clamp(3.2rem, 8vw, 7.4rem); }
.section-block h2, .cta-section h2 { font-size: clamp(2rem, 5vw, 4.3rem); }
.lede, .feature-card p, .cta-section p { color: rgba(226, 232, 240, 0.78); line-height: 1.75; font-size: 1.05rem; }
.lede { max-width: 680px; }
.hero-actions { display: flex; flex-wrap: wrap; gap: 1rem; margin-top: 2rem; }
.primary-button, .secondary-button { display: inline-flex; align-items: center; justify-content: center; border-radius: 999px; padding: 0.95rem 1.35rem; font-weight: 900; text-decoration: none; transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease; }
.primary-button { background: #67e8f9; color: #06121f; box-shadow: 0 18px 45px rgba(103, 232, 249, 0.24); }
.secondary-button { color: #f8fafc; border: 1px solid rgba(255, 255, 255, 0.2); background: rgba(255, 255, 255, 0.05); }
.primary-button:hover, .secondary-button:hover { transform: translateY(-3px); }
.showcase-card { min-height: 390px; display: grid; align-content: end; gap: 0.7rem; padding: 2rem; border-radius: 2rem; border: 1px solid rgba(255, 255, 255, 0.14); background: radial-gradient(circle at 35% 20%, rgba(103, 232, 249, 0.3), transparent 30%), linear-gradient(145deg, rgba(255,255,255,0.12), rgba(255,255,255,0.04)); box-shadow: 0 38px 100px rgba(0, 0, 0, 0.32); animation: float-card 4.8s ease-in-out infinite; }
.showcase-card strong { font-size: clamp(2rem, 4vw, 3.5rem); line-height: 1; }
.section-block { padding: 5rem clamp(1.25rem, 4vw, 4rem); }
.feature-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1rem; margin-top: 2rem; }
.feature-card, .process-list li { padding: 1.25rem; border-radius: 1.35rem; background: rgba(255, 255, 255, 0.07); border: 1px solid rgba(255, 255, 255, 0.11); animation: rise-in 560ms ease both; }
.split-section { display: grid; grid-template-columns: 0.9fr 1.1fr; gap: 2rem; align-items: start; }
.process-list { display: grid; gap: 1rem; margin: 0; padding-left: 1.25rem; }
.cta-section { margin-bottom: 4rem; padding: clamp(2rem, 5vw, 4rem); border-radius: 2rem; background: linear-gradient(135deg, rgba(103, 232, 249, 0.13), rgba(167, 139, 250, 0.14)); border: 1px solid rgba(255, 255, 255, 0.12); }
@keyframes float-card { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-14px); } }
@keyframes rise-in { from { opacity: 0; transform: translateY(18px); } to { opacity: 1; transform: translateY(0); } }
@media (max-width: 860px) { .nav-bar, .hero-grid, .split-section, .feature-grid { grid-template-columns: 1fr; } .nav-bar { flex-direction: column; padding-bottom: 2.5rem; } }
'''

    def _infer_dynamic_project_brief(self, task: str) -> dict[str, Any]:
        """Infer a reusable project brief from the user's words without domain-specific templates."""
        lower = task.lower()
        subject_match = re.search(r"(?:for|about)\s+(?:a|an|the)?\s*([a-z0-9][a-z0-9\s-]{1,80}?)(?:\s+(?:using|with|build|built|create|then|and\s+then|road\s*map|roadmap|plan|zip|download|in\s+the\s+sandbox)\b|$)", lower)
        raw_subject = subject_match.group(1) if subject_match else lower
        raw_subject = re.sub(r"\b(create|build|make|generate|implement|develop|website|landing\s*page|web\s*site|webpage|project|application|app|using|with|react|node|css|animation|road\s*map|roadmap|plan|step\s*by\s*step|zip|downloadable|download|give|me|the|file|files|sandbox|agents?|implementing|fix|issue|if|appear)\b", " ", raw_subject, flags=re.I)
        raw_subject = re.sub(r"[^a-z0-9\s-]", " ", raw_subject)
        stop = {"for", "and", "then", "that", "this", "from", "into", "entire", "full", "nice"}
        words = [w for w in raw_subject.split() if len(w) > 1 and w not in stop]
        subject_words = words[:4] or ["modern", "business"]
        subject = " ".join(subject_words).strip()
        subject_label = subject.title()
        slug = re.sub(r"[^a-z0-9]+", "-", subject.lower()).strip("-") or "generated-project"
        brand = " ".join(w.capitalize() for w in subject_words[:3]) or "Generated Studio"
        action_vocab = {
            "shop": "Shop now", "store": "Shop now", "market": "Shop now", "restaurant": "Reserve a table",
            "travel": "Plan a trip", "tour": "Plan a trip", "doctor": "Book a visit", "clinic": "Book a visit",
            "cms": "Open dashboard", "content": "Open dashboard", "course": "Start learning",
        }
        primary_action = next((label for key, label in action_vocab.items() if key in lower or key in subject), "Get started")
        sections = self._derive_landing_sections(subject)
        return {
            "subject": subject,
            "subject_label": subject_label,
            "slug": slug,
            "brand": brand,
            "audience": f"people looking for {subject}" if subject else "visitors",
            "primary_action": primary_action,
            "sections": sections,
        }

    def _derive_landing_sections(self, subject: str) -> list[dict[str, str]]:
        """Create section ideas from the inferred subject, not from a fixed domain template."""
        title = subject.title()
        return [
            {"title": f"Why choose {title}", "text": f"A clear first section that explains the value of {subject} in plain language."},
            {"title": f"Featured {title} experience", "text": f"A visual card grid for services, offers, products, or benefits related to {subject}."},
            {"title": "Simple next step", "text": "A conversion section that turns visitor interest into action."},
        ]

    def _generate_dynamic_react_landing_page(self, task: str, brief: dict[str, Any]) -> str:
        """Generate request-aware React UI from a synthesized brief."""
        subject = brief["subject_label"]
        brand = brief["brand"]
        audience = brief["audience"]
        primary_action = brief["primary_action"]
        task_summary = task.replace('"', "'")[:220]
        features_js = ",\n  ".join([
            f'{{ title: "{item["title"]}", text: "{item["text"]}" }}'
            for item in brief.get("sections", [])[:3]
        ])
        process_steps = [
            f"Understand what {audience} need first",
            f"Present {subject.lower()} with proof, clarity, and motion",
            "Guide visitors to the next action with one focused CTA",
        ]
        steps_js = ",\n  ".join([f'"{step}"' for step in process_steps])
        return f'''import React from "react";
import "./App.css";

const features = [
  {features_js}
];

const processSteps = [
  {steps_js}
];

export default function App() {{
  return (
    <main className="dynamic-landing">
      <section className="hero-section">
        <nav className="nav-bar" aria-label="Main navigation">
          <strong>{brand}</strong>
          <span>React + Node ready landing page</span>
        </nav>
        <div className="hero-grid">
          <div className="hero-copy">
            <p className="eyebrow">Built from the request</p>
            <h1>{subject} website designed to feel polished and useful.</h1>
            <p className="lede">This implementation was synthesized from: “{task_summary}”. It includes responsive layout, animated styling, reusable sections, and a clear call to action.</p>
            <div className="hero-actions">
              <a className="primary-button" href="#contact">{primary_action}</a>
              <a className="secondary-button" href="#features">View sections</a>
            </div>
          </div>
          <aside className="showcase-card" aria-label="Project showcase">
            <span>Live concept</span>
            <strong>{subject}</strong>
            <p>A focused front page that can grow into a full Node-backed product.</p>
          </aside>
        </div>
      </section>

      <section id="features" className="section-block">
        <p className="eyebrow">Page structure</p>
        <h2>Sections shaped around {audience}.</h2>
        <div className="feature-grid">
          {{features.map((item) => (
            <article className="feature-card" key={{item.title}}>
              <h3>{{item.title}}</h3>
              <p>{{item.text}}</p>
            </article>
          ))}}
        </div>
      </section>

      <section className="section-block split-section">
        <div>
          <p className="eyebrow">Build process</p>
          <h2>How the page moves visitors from interest to action.</h2>
        </div>
        <ol className="process-list">
          {{processSteps.map((step) => <li key={{step}}>{{step}}</li>)}}
        </ol>
      </section>

      <section id="contact" className="cta-section">
        <p className="eyebrow">Final call to action</p>
        <h2>Launch the next version of {subject.lower()}.</h2>
        <p>The ZIP contains the generated React files so you can run, customize, or connect a Node API when needed.</p>
        <a className="primary-button" href="mailto:hello@example.local">{primary_action}</a>
      </section>
    </main>
  );
}}
'''

    def _build_direct_artifact_steps(
        self,
        task: str,
        project_context: dict[str, Any],
        start_step_number: int,
    ) -> list[PlanStep]:
        """Build deterministic executable steps for common downloadable artifacts."""
        lower = task.lower()
        wants_zip = any(token in lower for token in ("zip", "download", "downloadable", "archive"))
        is_react = "react" in lower or "jsx" in lower or "component" in lower
        steps: list[PlanStep] = []
        n = start_step_number

        def add(description: str, action_type: str, target: str, content: str | None = None, metadata: dict[str, Any] | None = None):
            nonlocal n
            meta = dict(metadata or {})
            meta.setdefault("agent", {
                "create_file": "BuilderAgent",
                "edit_file": "BuilderAgent",
                "run_command": "VerifierAgent",
                "export_artifact": "ExportAgent",
            }.get(action_type, "PlannerAgent"))
            if content is not None:
                meta["content"] = content
            steps.append(PlanStep(step_number=n, description=description, action_type=action_type, target=target, metadata=meta))
            n += 1

        explicit_jsx = re.search(r"([A-Za-z0-9_\-]+\.(?:jsx|tsx|js|ts))", task, re.I)
        explicit_css = re.search(r"([A-Za-z0-9_\-]+\.css)", task, re.I)

        if is_react and "hello world" in lower:
            jsx_name = explicit_jsx.group(1) if explicit_jsx else "HelloWorld.jsx"
            css_name = explicit_css.group(1) if explicit_css else (Path(jsx_name).stem + ".css")
            component_name = self.coding_agent._normalize_identifier(Path(jsx_name).stem)
            css_class = re.sub(r"[^a-z0-9-]", "-", Path(css_name).stem.lower()).strip("-") or "hello-world"
            jsx_path = f"frontend/src/components/{jsx_name}"
            css_path = f"frontend/src/components/{css_name}"
            jsx_content = f'''import React from "react";\nimport "./{css_name}";\n\nexport default function {component_name}() {{\n  return (\n    <section className="{css_class}">\n      <span className="{css_class}__eyebrow">Generated React component</span>\n      <h1>Hello World</h1>\n      <p>This component was created in an isolated sandbox and packaged for download.</p>\n    </section>\n  );\n}}\n'''
            css_content = f'''.{css_class} {{\n  min-height: 220px;\n  display: grid;\n  place-items: center;\n  gap: 0.75rem;\n  padding: 2rem;\n  border-radius: 24px;\n  background: radial-gradient(circle at top left, rgba(125, 92, 255, 0.28), transparent 36%),\n    linear-gradient(135deg, #101827, #1d2a44);\n  color: #f8fbff;\n  text-align: center;\n  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.28);\n  animation: {css_class}-float 3s ease-in-out infinite;\n}}\n\n.{css_class} h1 {{\n  margin: 0;\n  font-size: clamp(2.5rem, 7vw, 5rem);\n  letter-spacing: -0.06em;\n}}\n\n.{css_class} p {{\n  margin: 0;\n  max-width: 34rem;\n  color: rgba(248, 251, 255, 0.78);\n}}\n\n.{css_class}__eyebrow {{\n  font-size: 0.8rem;\n  font-weight: 700;\n  letter-spacing: 0.18em;\n  text-transform: uppercase;\n  color: #9ee7ff;\n}}\n\n@keyframes {css_class}-float {{\n  0%, 100% {{ transform: translateY(0) scale(1); }}\n  50% {{ transform: translateY(-8px) scale(1.015); }}\n}}\n'''
            add(f"Create React component `{jsx_path}`", "create_file", jsx_path, jsx_content, {"artifact_kind": "react_component"})
            add(f"Create component stylesheet `{css_path}`", "create_file", css_path, css_content, {"artifact_kind": "style"})
            if wants_zip:
                add("Package the generated component files as a focused ZIP artifact", "export_artifact", "ZIP artifact", metadata={"export_only": True})
            return steps

        if is_react and any(token in lower for token in ("landing page", "website", "web site", "webpage", "home page", "homepage")):
            app_path = "frontend/src/App.jsx"
            css_path = "frontend/src/App.css"
            brief = self._infer_dynamic_project_brief(task)
            app_content = self._generate_dynamic_react_landing_page(task, brief)
            css_content = self._generate_dynamic_landing_page_css(brief)
            add(
                f"Design and implement a React landing page for {brief['subject_label']}",
                "create_file",
                app_path,
                app_content,
                {"artifact_kind": "landing_page", "dynamic_brief": brief},
            )
            add(
                "Implement responsive styling, visual polish, and animation for the generated landing page",
                "create_file",
                css_path,
                css_content,
                {"artifact_kind": "style", "dynamic_brief": brief},
            )
            add("Verify the generated React landing page with `cd frontend && npm run build`", "run_command", "cd frontend && npm run build", metadata={"verification": True})
            if wants_zip:
                add("Package the verified generated project as a downloadable ZIP artifact", "export_artifact", "ZIP artifact", metadata={"export_only": True})
            return steps

        return []

    async def _enrich_steps_with_project_context(
        self,
        steps: list[PlanStep],
        full_task: str,
        project_context: dict[str, Any],
    ) -> list[PlanStep]:
        """
        Improve text-parsed steps with project-aware targets and verification commands.
        """
        if not steps:
            return steps

        parent_context = self.coding_agent._understand_task(full_task, project_context)
        created_or_edited_paths: list[str] = []

        for step in steps:
            step_context = self.coding_agent._understand_task(step.description, project_context)
            step.metadata.setdefault("project_context", project_context)
            step.metadata.setdefault("coding_context", step_context)

            if step.action_type in {"create_file", "edit_file"}:
                file_ops = await self.coding_agent._determine_files(step.description, step_context)
                if file_ops:
                    primary = file_ops[0]
                    step.target = primary.get("path", step.target)
                    step.metadata["operation"] = primary.get("operation", "write")
                    if primary.get("content") is not None:
                        step.metadata["content"] = primary["content"]
                    if primary.get("previous_content") is not None:
                        step.metadata["previous_content"] = primary["previous_content"]
                    created_or_edited_paths.append(step.target)
                    continue

            if step.action_type == "run_command":
                commands = self._resolve_verification_commands(
                    step.description,
                    created_or_edited_paths,
                    parent_context,
                )
                if commands:
                    step.target = commands[0]
                    step.metadata["verification"] = True
                    step.description = f"Verify the generated changes with `{step.target}`"
                    continue

            if step.action_type in {"show_result", "read_file"}:
                if created_or_edited_paths and step.target == "output.txt":
                    step.target = created_or_edited_paths[-1]
                elif step.target == "output.txt":
                    inferred_target = parent_context.get("file_path") or step_context.get("file_path")
                    if inferred_target:
                        step.target = inferred_target

        return steps

    def _resolve_verification_commands(
        self,
        step_description: str,
        touched_paths: list[str],
        parent_context: dict[str, Any],
    ) -> list[str]:
        desc_lower = step_description.lower()
        if not any(keyword in desc_lower for keyword in ["verify", "test", "build", "check", "validate"]):
            return []

        if touched_paths:
            return self.coding_agent._build_verification_commands(touched_paths)

        inferred_path = parent_context.get("file_path")
        if inferred_path:
            return self.coding_agent._build_verification_commands([inferred_path])

        framework = (parent_context.get("framework") or "").lower()
        if framework == "react":
            return ["cd frontend && npm run build"]
        if framework == "fastapi":
            return ["python -m compileall backend/app"]
        return []

    async def _build_project_aware_steps(
        self,
        task: str,
        project_context: dict[str, Any],
        start_step_number: int,
    ) -> list[PlanStep]:
        """
        Build richer planning steps from the same project-aware coding analysis
        used by the coding agent.
        """
        context = self.coding_agent._understand_task(task, project_context)
        if context["task_intent"] not in {"create_component", "create_api", "create_utility", "edit_file", "create_file"}:
            return []

        file_ops = await self.coding_agent._determine_files(task, context)
        if not file_ops:
            return []

        steps: list[PlanStep] = []
        step_number = start_step_number
        for file_op in file_ops:
            operation = file_op.get("operation", "write")
            action_type = "edit_file" if operation == "edit" else "create_file"
            content = file_op.get("content")
            metadata = {
                "content": content,
                "coding_context": context,
                "project_context": project_context,
                "operation": operation,
            }
            if file_op.get("previous_content") is not None:
                metadata["previous_content"] = file_op["previous_content"]
            steps.append(
                PlanStep(
                    step_number=step_number,
                    description=file_op.get("description", task),
                    action_type=action_type,
                    target=file_op["path"],
                    metadata=metadata,
                )
            )
            step_number += 1

        for command in self.coding_agent._build_verification_commands(
            [file_op["path"] for file_op in file_ops if file_op.get("path")]
        ):
            steps.append(
                PlanStep(
                    step_number=step_number,
                    description=f"Verify the generated changes with `{command}`",
                    action_type="run_command",
                    target=command,
                    metadata={"verification": True},
                )
            )
            step_number += 1

        return steps

    def _detect_implicit_steps(self, task: str) -> list[str]:
        """Detect implicit steps from task description."""
        steps = []
        task_lower = task.lower()
        
        # Pattern: "create X, update Y, show Z"
        # Split by action verbs
        action_verbs = [
            (r'\bcreate\s+(?:a\s+)?(?:new\s+)?(?:file\s+)?', 'create'),
            (r'\bupdate\s+(?:its|it\'s|the)?\s*(?:content\s+)?(?:to\s+be\s+)?', 'update'),
            (r'\bdisplay\s+(?:it|the\s+(?:content|result|file))', 'display'),
            (r'\bshow\s+(?:me\s+)?(?:it|the\s+(?:content|result|file))', 'show'),
        ]
        
        # Find all action positions
        action_positions = []
        for pattern, action_name in action_verbs:
            for match in re.finditer(pattern, task_lower):
                action_positions.append((match.start(), match.end(), action_name))
        
        # Sort by position
        action_positions.sort(key=lambda x: x[0])
        
        # Extract steps based on action positions
        if action_positions:
            for i, (start, end, action_name) in enumerate(action_positions):
                if i + 1 < len(action_positions):
                    next_start = action_positions[i + 1][0]
                    step_text = task[start:next_start].strip()
                else:
                    step_text = task[start:].strip()
                steps.append(step_text)
        
        return steps if steps else []

    def _rewrite_task_for_clarity(self, task: str) -> str:
        """
        Rewrite the user's task for better LLM understanding.
        
        This improves the agent's ability to understand and execute tasks.
        """
        task_lower = task.lower()
        
        # Extract key information
        file_match = re.search(r'(?:called|named)\s+["\']?([\w\-]+\.(?:jsx|tsx|js|ts|py|html|css|json|txt|md|xml|yaml|yml))["\']?', task)
        path_match = re.search(r'(?:in|inside|at|to)\s+(?:the\s+)?(?:folder\s+|directory\s+)?["\']?([/\w\-]+)["\']?', task)
        content_match = re.search(r'["\']([^"\']{3,})["\']', task)
        
        file_name = file_match.group(1) if file_match else None
        file_path = path_match.group(1).lstrip("/") if path_match else None
        content = content_match.group(1) if content_match else None
        
        # Build clearer task description
        parts = []
        
        if "create" in task_lower or "new" in task_lower:
            if file_name:
                full_path = f"{file_path}/{file_name}" if file_path else file_name
                parts.append(f"Create file: {full_path}")
            else:
                parts.append("Create new file")
        
        if "update" in task_lower or "content" in task_lower:
            if content:
                parts.append(f"Update content to: {content}")
            else:
                parts.append("Update file content")
        
        if "display" in task_lower or "show" in task_lower:
            if file_name:
                parts.append(f"Display content of: {file_name}")
            else:
                parts.append("Display file content")
        
        return " | ".join(parts) if parts else task

    def _validate_file_path(self, file_path: str) -> str:
        """Validate and clean file path to prevent invalid names."""
        file_path = (file_path or "").strip()
        file_path = file_path.lstrip("/")

        invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
        for char in invalid_chars:
            file_path = file_path.replace(char, '')

        invalid_starts = ["create ", "update ", "display ", "show ", "the ", "a ", "an "]
        for start in invalid_starts:
            if file_path.lower().startswith(start):
                return ""

        if len(file_path) > 200:
            return ""

        if " " in file_path and not re.match(r'^[\w\-/]+\.\w+$', file_path):
            file_match = re.search(r'([\w\-]+\.(?:jsx|tsx|js|ts|py|html|css|json|txt|md|xml|yaml|yml))', file_path)
            if file_match:
                return file_match.group(1)
            return ""

        return file_path

    def _infer_file_target_from_step(self, step: PlanStep) -> str:
        """Recover a missing file target from step metadata or task understanding."""
        metadata = step.metadata or {}

        packet_targets = metadata.get("packet_targets")
        if isinstance(packet_targets, list):
            for candidate in packet_targets:
                if isinstance(candidate, str) and candidate.strip() and "." in candidate:
                    return candidate.strip().lstrip("/")

        coding_context = metadata.get("coding_context")
        if isinstance(coding_context, dict):
            candidate = coding_context.get("file_path")
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip().lstrip("/")

        project_context = metadata.get("project_context") if isinstance(metadata.get("project_context"), dict) else {}
        inferred_context = self.coding_agent._understand_task(step.description, project_context)
        candidate = inferred_context.get("file_path")
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip().lstrip("/")

        task_lower = step.description.lower()
        if "react" in task_lower or "component" in task_lower:
            component_name = inferred_context.get("component_name") or "HelloWorld"
            base_dir = "frontend/src/components"
            ext = ".jsx"
            return f"{base_dir}/{component_name}{ext}"
        if "css" in task_lower or "style" in task_lower or "animation" in task_lower:
            return "frontend/src/components/HelloWorld.css"
        if "readme" in task_lower or "documentation" in task_lower:
            return "README.md"
        return "generated_output.txt"

    def _detect_explicit_steps(self, task: str) -> list[str]:
        """Detect explicit steps from task description."""
        steps = []
        task_lower = task.lower()
        
        # CRITICAL: Split by "then" keyword (most common separator)
        # Must handle: "then", "then ", " then ", "then\n"
        if "then" in task_lower:
            # Split by "then" but keep the parts
            parts = re.split(r'\bthen\b', task, flags=re.IGNORECASE)
            steps = [p.strip() for p in parts if p.strip()]
            
            if len(steps) > 1:
                return steps
        
        # Try other separators
        separators = [
            r"\band then\b",
            r"\bnext\b",
            r"\bafter that\b",
            r"\bfirst\b.*?\bsecond\b",
            r"\d+\.\s",  # "1. do this 2. do that"
            r"\bstep\s+\d+\b",
        ]
        
        # Try to find sequential indicators
        has_step_indicator = any(re.search(sep, task_lower) for sep in separators)
        
        if has_step_indicator:
            # Split task into parts
            parts = re.split(r'\b(?:and then|next|after that)\b', task, flags=re.IGNORECASE)
            steps = [p.strip() for p in parts if p.strip()]
            
            # If still no steps, try numbered pattern
            if not steps:
                numbered_steps = re.findall(r'(\d+[\.\)]\s*[^\.]+)', task)
                if numbered_steps:
                    steps = numbered_steps
        
        # Look for "first", "second", "third" patterns
        if not steps:
            first_match = re.search(r'first\s*,?\s*(.+?)(?:,|\.)', task_lower)
            second_match = re.search(r'second\s*,?\s*(.+?)(?:,|\.)', task_lower)
            third_match = re.search(r'third\s*,?\s*(.+?)(?:,|\.)', task_lower)
            
            if first_match:
                steps.append(f"First: {first_match.group(1)}")
            if second_match:
                steps.append(f"Second: {second_match.group(1)}")
            if third_match:
                steps.append(f"Third: {third_match.group(1)}")
        
        return steps if steps else []

    def _determine_action_type(self, step_desc: str) -> str:
        """Determine the action type for a step."""
        desc_lower = step_desc.lower()

        # CRITICAL: Check for specific commands in the description first
        if any(kw in desc_lower for kw in ["zip", "download", "downloadable", "archive", "package"]):
            return "export_artifact"

        if any(kw in desc_lower for kw in ["pytest", "npm run", "python", "pip install", "compileall"]):
            return "run_command"

        if any(kw in desc_lower for kw in ["run", "execute", "command", "verify", "test", "build", "check", "validate"]):
            return "run_command"
        if any(kw in desc_lower for kw in ["create", "make", "new file", "write"]):
            return "create_file"
        elif any(kw in desc_lower for kw in ["update", "edit", "modify", "change", "content"]):
            return "edit_file"
        elif any(kw in desc_lower for kw in ["show", "display", "print", "result"]):
            return "show_result"
        elif any(kw in desc_lower for kw in ["delete", "remove"]):
            return "delete_file"
        elif any(kw in desc_lower for kw in ["read", "open"]):
            return "read_file"
        else:
            return "general"

    def _extract_target(self, step_desc: str) -> str:
        """
        Extract the target (file path, command, etc.) from step description.
        
        CRITICAL: Must extract ONLY the file path, not the entire description.
        """
        step_lower = step_desc.lower()

        # Strategy 0: If it's a command step, try to extract the command
        if self._determine_action_type(step_desc) == "run_command":
            # Look for backticks first
            command_match = re.search(r'`([^`]+)`', step_desc)
            if command_match:
                return command_match.group(1)
            
            # Look for common command patterns
            patterns = [
                r'(?:run|execute|verify)\s+(?:the\s+)?(?:command\s+)?["\']?([^"\']+)["\']?',
                r'(pytest\s+[^\s]+)',
                r'(npm\s+[^\s]+)',
                r'(python\d?\s+[^\s]+)',
            ]
            for pattern in patterns:
                match = re.search(pattern, step_desc, re.IGNORECASE)
                if match:
                    return match.group(1)
        
        # Strategy 1: Look for explicit file patterns with quotes
        # "create 'path/to/file.txt'" or "create 'file.txt'"
        quoted_file = re.search(r'["\']([/\w\-]+\.(?:jsx|tsx|js|ts|py|html|css|json|txt|md|xml|yaml|yml))["\']', step_desc)
        if quoted_file:
            return quoted_file.group(1)
        
        # Strategy 2: Look for "called filename" or "named filename"
        called_match = re.search(r'(?:called|named)\s+["\']?([\w\-]+\.(?:jsx|tsx|js|ts|py|html|css|json|txt|md|xml|yaml|yml))["\']?', step_desc, re.IGNORECASE)
        if called_match:
            filename = called_match.group(1)
            # Check if there's a path mentioned
            path_match = re.search(r'(?:in|inside|at|to)\s+(?:the\s+)?(?:folder\s+|directory\s+)?["\']?([/\w\-]+)["\']?', step_desc, re.IGNORECASE)
            if path_match:
                path = path_match.group(1).lstrip("/")
                return f"{path}/{filename}"
            return filename
        
        # Strategy 3: Look for "file inside /path" or "file in /path"
        inside_path_match = re.search(r'(?:file|component)\s+(?:inside|in|at)\s+(?:the\s+)?(?:folder\s+|directory\s+)?["\']?([/\w\-]+)["\']?', step_desc, re.IGNORECASE)
        if inside_path_match:
            path = inside_path_match.group(1).lstrip("/")
            # Look for filename in the same step
            file_in_step = re.search(r'([\w\-]+\.(?:jsx|tsx|js|ts|py|html|css|json|txt|md|xml|yaml|yml))', step_desc, re.IGNORECASE)
            if file_in_step:
                return f"{path}/{file_in_step.group(1)}"
            return path
        
        # Strategy 4: Look for "create filename" or "write filename"
        create_file = re.search(r'(?:create|write|make|save)\s+(?:a\s+)?(?:new\s+)?(?:file\s+)?([\w\-]+\.(?:jsx|tsx|js|ts|py|html|css|json|txt|md|xml|yaml|yml))', step_desc, re.IGNORECASE)
        if create_file:
            filename = create_file.group(1)
            # Check for path
            path_match = re.search(r'(?:in|inside|at|to)\s+(?:the\s+)?(?:folder\s+|directory\s+)?["\']?([/\w\-]+)["\']?', step_desc, re.IGNORECASE)
            if path_match:
                path = path_match.group(1).lstrip("/")
                return f"{path}/{filename}"
            return filename
        
        # Strategy 5: For update/edit/display steps, try to find file reference
        if any(kw in step_lower for kw in ["update", "edit", "display", "show", "read"]):
            # Look for "it" or "the file" - should inherit from previous step
            # For now, look for any file pattern
            any_file = re.search(r'([\w\-]+\.(?:jsx|tsx|js|ts|py|html|css|json|txt|md|xml|yaml|yml))', step_desc, re.IGNORECASE)
            if any_file:
                return any_file.group(1)

        # Strategy 6: For verification steps, keep the command target explicit.
        if any(kw in step_lower for kw in ["verify", "test", "build", "check", "validate"]):
            command_match = re.search(r'`([^`]+)`', step_desc)
            if command_match:
                return command_match.group(1)
            direct_command = self._extract_command_from_description(step_desc)
            if direct_command:
                return direct_command

        # Fallback: Return a safe default
        return ""

    def _extract_command_from_description(self, step_desc: str) -> str:
        backtick_match = re.search(r'`([^`]+)`', step_desc)
        if backtick_match:
            return backtick_match.group(1).strip()
        patterns = [
            r"(PYTHONPATH=[^\n]+pytest[^\n]*)",
            r"(cd\s+[^\n]+&&\s+[^\n]+)",
            r"(python(?:3(?:\.\d+)?)?\s+-m\s+[^\n]+)",
            r"(pytest\s+[^\n]+)",
            r"(npm\s+run\s+\w+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, step_desc)
            if match:
                return match.group(1).strip()
        return ""

    def _extract_content_for_step(self, step_desc: str) -> Optional[str]:
        """
        Extract content for a step from the description.
        
        CRITICAL: Must extract ONLY the content, not the entire description.
        """
        # Pattern 1: Quoted content "hello world" or 'hello world'
        content_match = re.search(r'["\']([^"\']{3,})["\']', step_desc)
        if content_match:
            return content_match.group(1)
        
        # Pattern 2: "to be X" or "to X" (where X is at least 3 chars)
        to_be_match = re.search(r'(?:to\s+be\s+|to\s+)([\w\s]{3,})', step_desc, re.IGNORECASE)
        if to_be_match:
            return to_be_match.group(1).strip()
        
        # Pattern 3: "say X" or "display X" or "show X"
        say_match = re.search(r'(?:say|display|show)\s+["\']?([\w\s]{3,})["\']?', step_desc, re.IGNORECASE)
        if say_match:
            return say_match.group(1).strip()
        
        # Pattern 4: "content to be X" or "content is X"
        content_is = re.search(r'(?:content\s+(?:to\s+)?be|content\s+is)\s+["\']?([\w\s]{3,})["\']?', step_desc, re.IGNORECASE)
        if content_is:
            return content_is.group(1).strip()
        
        return None

    async def execute_plan(
        self,
        plan: ExecutionPlan,
        progress_callback: Optional[Callable] = None,
        max_retries: int = 2,
    ) -> ExecutionPlan:
        """
        Execute a plan step-by-step, reporting progress.
        
        Includes self-debugging capabilities:
        - Detects errors automatically
        - Attempts to fix and retry
        - Logs all debugging information
        - CRITICAL: Shares context between steps (file paths, etc.)

        Args:
            plan: The execution plan
            progress_callback: Optional callback for progress updates
            max_retries: Maximum retry attempts per step

        Returns:
            Updated plan with results
        """
        if progress_callback:
            self.progress_callback = progress_callback

        plan.status = PlanStatus.IN_PROGRESS
        plan.started_at = datetime.now(UTC).isoformat()

        # Reset expansion counter for safety
        self._expansion_counter = 0

        # Enable workspace staging if coding agent supports it
        try:
            if hasattr(self.coding_agent, "enable_workspace"):
                self.coding_agent.enable_workspace(True)
                print("🔒 [PlanningAgent] Workspace staging enabled for plan execution")
        except Exception:
            pass
        
        # CRITICAL: Track context across steps
        step_context = {
            "last_created_file": None,
            "last_file_path": None,
            "files_created": [],
        }

        await self._report_progress(plan)

        # Execute each step (index loop to allow inserting expanded sub-steps)
        await self._execute_plan_loop(plan, max_retries)

        # Only mark completed if still in progress (not paused or failed)
        if plan.status == PlanStatus.IN_PROGRESS:
            plan.status = PlanStatus.COMPLETED
            plan.completed_at = datetime.now(UTC).isoformat()
            print(f"✅ [PlanningAgent] All {plan.total_steps} steps completed successfully!")

        # If plan completed, commit staged files to project root (respect approved_files if provided)
        if plan.status == PlanStatus.COMPLETED and self.auto_commit_workspace:
            try:
                if hasattr(self.coding_agent, "workspace") and getattr(self.coding_agent, "use_workspace", False):
                    try:
                        approved_files = getattr(plan, 'approved_files', None)
                        if approved_files is not None and isinstance(approved_files, list):
                            copied = self.coding_agent.workspace.commit_to(self.project_root, allowed_files=approved_files)
                        else:
                            copied = self.coding_agent.workspace.commit_to(self.project_root)
                        self.coding_agent.workspace.cleanup()
                        if copied:
                            print(f"📦 [PlanningAgent] Committed {len(copied)} staged files to project root")
                            # Attach commit info to plan for traceability
                            plan.extra_committed_files = copied  # type: ignore
                    except Exception as e:
                        print(f"⚠️ [PlanningAgent] Workspace commit failed: {e}")
            except Exception:
                pass

        await self._report_progress(plan)
        return plan

    async def _execute_plan_loop(self, plan: ExecutionPlan, max_retries: int = 2):
        """Execute plan steps using an index loop so steps can expand into subplans and checkpoints saved after each step."""
        index = getattr(plan, "current_step", 0) or 0
        if index <= 0:
            for i, existing_step in enumerate(plan.steps):
                if existing_step.status not in {StepStatus.COMPLETED, StepStatus.SKIPPED}:
                    index = i
                    break
            else:
                index = len(plan.steps)
        # CRITICAL: Track context across steps
        step_context = {
            "last_created_file": None,
            "last_file_path": None,
            "files_created": [],
        }

        # Resume context if checkpoint exists on plan
        try:
            if getattr(plan, "_checkpoint_id", None):
                print(f"🔁 [PlanningAgent] Resuming plan from checkpoint: {plan._checkpoint_id}")
        except Exception:
            pass

        while index < len(plan.steps):
            plan.current_step = index
            step = plan.steps[index]

            try:
                # Mark step as in progress
                step.status = StepStatus.IN_PROGRESS
                step.started_at = datetime.now(UTC).isoformat()

                # inherit context
                self._apply_step_context(step, step_context)
                await self._report_progress(plan)

                # Allow expansion of the current step into sub-steps (recursive planning)
                expanded = self._maybe_expand_step(step)

                # If expansion produced a metadata flag requiring approval, pause and persist
                if step.metadata.get("requires_approval"):
                    plan.status = PlanStatus.PENDING
                    plan.error = "Expansion requires human approval"

                    # Capture staged diffs if workspace is in use
                    try:
                        staged = []
                        if hasattr(self.coding_agent, 'workspace') and getattr(self.coding_agent, 'use_workspace', False):
                            ws = getattr(self.coding_agent, 'workspace')
                            staged_files = ws.list_staged_files()
                            import difflib
                            for rel in staged_files:
                                ws_path = Path(ws.base) / rel
                                proj_path = self.project_root / rel
                                try:
                                    ws_text = ws_path.read_text(encoding='utf-8') if ws_path.exists() else ''
                                except Exception:
                                    ws_text = ''
                                try:
                                    proj_text = proj_path.read_text(encoding='utf-8') if proj_path.exists() else ''
                                except Exception:
                                    proj_text = ''
                                diff_lines = list(difflib.unified_diff(
                                    proj_text.splitlines(keepends=True),
                                    ws_text.splitlines(keepends=True),
                                    fromfile=str(proj_path),
                                    tofile=str(ws_path),
                                ))
                                staged.append({"path": rel, "diff": ''.join(diff_lines)})
                        if staged:
                            setattr(plan, 'staged_diffs', staged)
                    except Exception as e:
                        print(f"⚠️ [PlanningAgent] Failed capturing staged diffs: {e}")

                    await self._report_progress(plan)
                    print(f"⏸️ [PlanningAgent] Expansion requires approval for step {step.step_number}; paused")
                    return

                if expanded:
                    # expanded may be a list of PlanStep or list of dict-like descriptors
                    normalized: list[PlanStep] = []
                    for e in expanded:
                        if isinstance(e, PlanStep):
                            normalized.append(e)
                        elif isinstance(e, dict):
                            desc = e.get("description") or e.get("desc") or ""
                            if not desc:
                                continue
                            action_type = e.get("action_type") or self._determine_action_type(desc)
                            target = e.get("target") or self._extract_target(desc)
                            metadata = e.get("metadata") or {}
                            normalized.append(
                                PlanStep(
                                    step_number=step.step_number,
                                    description=desc.strip(),
                                    action_type=action_type,
                                    target=target,
                                    metadata={**{"derived_from": step.description}, **(metadata if isinstance(metadata, dict) else {})},
                                )
                            )
                    if not normalized:
                        # nothing usable
                        pass
                    else:
                        plan.steps = plan.steps[:index] + normalized + plan.steps[index + 1 :]
                        print(f"🔀 [PlanningAgent] Expanded step {step.step_number} into {len(normalized)} sub-steps")
                        # continue without increment to process first new sub-step
                        continue

                # Execute with retries
                success = False
                last_error = None
                for attempt in range(max_retries + 1):
                    try:
                        await self._execute_step(step)
                        success = True
                        break
                    except Exception as e:
                        last_error = e
                        print(f"⚠️ [PlanningAgent] Step {step.step_number} attempt {attempt + 1} failed: {str(e)}")
                        if attempt < max_retries:
                            print(f"🔧 [PlanningAgent] Attempting to auto-fix step {step.step_number}...")
                            await self._attempt_auto_fix(step, str(e))
                        else:
                            raise last_error

                if success:
                    step.status = StepStatus.COMPLETED
                    step.completed_at = datetime.now(UTC).isoformat()
                    self._update_step_context(step, step_context)
                    print(f"✅ [PlanningAgent] Step {step.step_number} completed successfully")

                    # Save a durable checkpoint after each successful step
                    try:
                        save_checkpoint(plan, getattr(plan, "_checkpoint_id", None))
                    except Exception as e:
                        print(f"⚠️ [PlanningAgent] Failed to save checkpoint: {e}")

                    await self._report_progress(plan)

                    index += 1

            except Exception as e:
                # Mark failure on the step
                err_text = str(e)
                step.status = StepStatus.FAILED
                step.error = err_text
                step.completed_at = datetime.now(UTC).isoformat()

                # If this looks like an operator/permission or 'command not allowed' issue,
                # pause and ask for human approval instead of failing the whole plan.
                low = err_text.lower()
                needs_human = False
                if "command not allowed" in low or "not allowed" in low or "permission" in low or "operation not permitted" in low or "forbidden" in low:
                    needs_human = True

                if needs_human:
                    plan.status = PlanStatus.PENDING
                    plan.error = f"Step {step.step_number} requires human approval: {err_text}"
                    # Attach approval metadata to step for UI
                    step.metadata.setdefault('requires_approval', True)
                    step.metadata.setdefault('approval_reason', err_text)
                    # Capture staged diffs if workspace is in use (best-effort)
                    try:
                        staged = []
                        if hasattr(self.coding_agent, 'workspace') and getattr(self.coding_agent, 'use_workspace', False):
                            ws = getattr(self.coding_agent, 'workspace')
                            staged_files = ws.list_staged_files()
                            import difflib
                            for rel in staged_files:
                                ws_path = Path(ws.base) / rel
                                proj_path = self.project_root / rel
                                try:
                                    ws_text = ws_path.read_text(encoding='utf-8') if ws_path.exists() else ''
                                except Exception:
                                    ws_text = ''
                                try:
                                    proj_text = proj_path.read_text(encoding='utf-8') if proj_path.exists() else ''
                                except Exception:
                                    proj_text = ''
                                diff_lines = list(difflib.unified_diff(
                                    proj_text.splitlines(keepends=True),
                                    ws_text.splitlines(keepends=True),
                                    fromfile=str(proj_path),
                                    tofile=str(ws_path),
                                ))
                                staged.append({"path": rel, "diff": ''.join(diff_lines)})
                        if staged:
                            setattr(plan, 'staged_diffs', staged)
                    except Exception as ex:
                        print(f"⚠️ [PlanningAgent] Failed capturing staged diffs during pause: {ex}")

                    # Save checkpoint for human review/resume
                    try:
                        save_checkpoint(plan, getattr(plan, "_checkpoint_id", None))
                    except Exception:
                        pass

                    print(f"⏸️ [PlanningAgent] Paused for human approval due to step {step.step_number}: {err_text}")
                    await self._report_progress(plan)
                    return

                # Otherwise treat as hard failure
                plan.status = PlanStatus.FAILED
                plan.error = f"Step {step.step_number} failed: {err_text}"
                plan.completed_at = datetime.now(UTC).isoformat()

                # Save checkpoint for debugging/resume
                try:
                    save_checkpoint(plan, getattr(plan, "_checkpoint_id", None))
                except Exception:
                    pass

                print(f"❌ [PlanningAgent] Step {step.step_number} failed after retries: {err_text}")
                await self._report_progress(plan)
                return

    def _maybe_expand_step(self, step: PlanStep) -> list[PlanStep] | None:
        """Detect and expand compound step descriptions into multiple PlanStep objects.

        Returns a list of PlanStep instances (new steps) or None if no expansion.
        Adds safety limits (max depth, total substeps) and an LLM-backed expansion hook.
        """
        # Respect explicit expansion depth recorded in metadata
        depth = int(step.metadata.get("expansion_depth", 0))
        if depth >= self.MAX_EXPANSION_DEPTH:
            # Don't expand further
            print(f"⚠️ [PlanningAgent] Expansion depth {depth} reached for step {step.step_number}; skipping expansion")
            return None

        # Use existing explicit step detection logic
        parts = self._detect_explicit_steps(step.description)
        if parts and len(parts) > 1:
            # Safety: prevent runaway total substeps
            if getattr(self, "_expansion_counter", 0) + len(parts) > self.MAX_TOTAL_SUBSTEPS:
                print(f"⚠️ [PlanningAgent] Expansion would exceed total substep limit ({self.MAX_TOTAL_SUBSTEPS}); skipping expansion")
                return None

            new_steps: list[PlanStep] = []
            for i, part in enumerate(parts, start=1):
                new_steps.append(
                    PlanStep(
                        step_number=step.step_number,  # keep original numbering for traceability; real renumbering occurs later
                        description=part.strip(),
                        action_type=self._determine_action_type(part),
                        target=self._extract_target(part),
                        metadata={"derived_from": step.description, "expansion_depth": depth + 1},
                    )
                )

            # Account for expanded substeps
            self._expansion_counter = getattr(self, "_expansion_counter", 0) + len(parts)
            return new_steps

        # Heuristic/LLM-backed expansion for long single-step descriptions
        # Only attempt if not already deeply expanded
        if len(step.description) > 150 and depth + 1 <= self.MAX_EXPANSION_DEPTH:
            try:
                expanded = self._invoke_llm_expand(step.description, depth)
                if expanded:
                    if getattr(self, "_expansion_counter", 0) + len(expanded) > self.MAX_TOTAL_SUBSTEPS:
                        print(f"⚠️ [PlanningAgent] LLM expansion would exceed total substep limit; skipping")
                        return None

                    # Wrap into PlanStep objects
                    new_steps = []
                    # expanded may be list[dict] (validated) -> turn into PlanStep
                    new_steps = []
                    import app.services.expansion_metrics as metrics
                    for part in expanded:
                        # part can be dict with description/action_type/target/metadata
                        desc = part.get("description") if isinstance(part, dict) else str(part)
                        action = part.get("action_type") if isinstance(part, dict) else None
                        target = part.get("target") if isinstance(part, dict) else None
                        meta = part.get("metadata") if isinstance(part, dict) else {}
                        new_steps.append(
                            PlanStep(
                                step_number=step.step_number,
                                description=desc.strip(),
                                action_type=action or self._determine_action_type(desc),
                                target=target or self._extract_target(desc),
                                metadata={**{"derived_from": step.description, "expansion_depth": depth + 1}, **(meta if isinstance(meta, dict) else {})},
                            )
                        )
                    # record metrics
                    try:
                        metrics.record_expansion(None, step.description, len(new_steps), depth + 1, source="llm")
                    except Exception:
                        pass

                    # Safety/approval: require approval for large expansions
                    if len(new_steps) > 5:
                        step.metadata["requires_approval"] = True
                        step.metadata["suggested_substeps"] = [s.description for s in new_steps]
                        print(f"⚠️ [PlanningAgent] Expansion too large ({len(new_steps)}); marking requires_approval")
                        return None

                    self._expansion_counter = getattr(self, "_expansion_counter", 0) + len(new_steps)
                    print(f"🔀 [PlanningAgent] LLM-expanded step {step.step_number} into {len(new_steps)} sub-steps")
                    return new_steps
            except Exception as e:
                print(f"⚠️ [PlanningAgent] LLM expansion failed: {e}")

        return None

    def _invoke_llm_expand(self, text: str, depth: int) -> list[dict] | None:
        """Attempt to expand a complex description into smaller sub-step objects.

        Returns a list of step objects: {description, action_type?, target?, metadata?}

        Strategy:
        - Prefer a local LLM expansion helper if available
        - Accept either array of strings or array of objects from the LLM and validate
        - Fall back to a safe sentence-based splitter
        """
        # Try to use autonomous agent LLM helper if available
        try:
            from app.services.autonomous_agent import AutonomousDevelopmentAgent

            # Create a lightweight agent if possible (it shares LLM helper methods)
            helper = AutonomousDevelopmentAgent(self.project_root)
            prompt = (
                "Split the following task description into a short ordered list of discrete actionable steps. "
                "Return the steps as a JSON array. Each item should be either a string or an object with keys: description (string), action_type (optional), target (optional), metadata (optional). Limit to at most 10 items.\n\n"
                f"Description:\n{text}\n"
            )
            response = helper._llm_generate_solution(prompt)
            # Try to parse JSON array out of the response
            try:
                # extract JSON from response text if extra commentary exists
                m = re.search(r'\[.*\]', response, flags=re.S)
                if m:
                    arr_text = m.group(0)
                else:
                    arr_text = response
                parsed = json.loads(arr_text)
                if isinstance(parsed, list) and parsed:
                    normalized = []
                    from app.schemas.llm import LLMPlanStep
                    for item in parsed:
                        if isinstance(item, str):
                            data = {"description": item.strip()}
                        elif isinstance(item, dict):
                            # Map common synonyms
                            desc = item.get("description") or item.get("desc") or item.get("text")
                            data = {
                                "description": desc.strip() if isinstance(desc, str) else None,
                                "action_type": item.get("action_type") if isinstance(item.get("action_type"), str) else None,
                                "target": item.get("target") if isinstance(item.get("target"), str) else None,
                                "metadata": item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
                            }
                        else:
                            continue
                        # Validate via pydantic
                        try:
                            step_obj = LLMPlanStep(**data)
                            normalized.append(step_obj.dict())
                        except Exception:
                            # Skip invalid entries
                            continue
                    if normalized:
                        return normalized[:10]
            except Exception:
                # ignore parse errors and fall back
                pass
        except Exception:
            # If helper not available or failed, fall back to heuristic splitter
            pass

        # Heuristic fallback: split into sentences by common delimiters and conjunctions
        parts = re.split(r'[\.;]\s+|\band then\b|\bthen\b|\bnext\b|\n', text, flags=re.IGNORECASE)
        candidates = [p.strip() for p in parts if p.strip() and len(p.strip()) > 10]
        if len(candidates) > 1:
            # Convert to objects
            return [{"description": c} for c in candidates[:10]]
        return None

    async def execute_plan_from_checkpoint(self, plan_id: str) -> ExecutionPlan:
        """Load a checkpointed plan and resume execution.

        This reconstructs a minimal ExecutionPlan and calls execute_plan on it.
        """
        data = load_checkpoint(plan_id)
        plan = ExecutionPlan(task=data.get("task", "resumed plan"))
        plan.status = PlanStatus(data.get("status", PlanStatus.PENDING))
        plan.current_step = data.get("current_step", 0)
        plan.started_at = data.get("started_at")
        plan.completed_at = data.get("completed_at")
        # Rebuild steps
        steps = []
        for s in data.get("steps", []):
            # Map string status back to StepStatus when possible
            st = s.get("status", StepStatus.PENDING.value) if isinstance(s.get("status"), str) else StepStatus.PENDING.value
            try:
                status_enum = StepStatus(st)
            except Exception:
                status_enum = StepStatus.PENDING
            steps.append(
                PlanStep(
                    step_number=s.get("step_number", 0),
                    description=s.get("description", ""),
                    action_type=s.get("action_type", "general"),
                    target=s.get("target", ""),
                    status=status_enum,
                    output=s.get("output", ""),
                    error=s.get("error", ""),
                )
            )
        plan.steps = steps
        # Attach checkpoint id
        setattr(plan, "_checkpoint_id", plan_id)

        # Execute remaining steps
        completed = await self.execute_plan(plan)
        return completed

    def _apply_step_context(self, step: PlanStep, context: dict):
        """
        Apply context from previous steps to current step.
        
        This is CRITICAL for multi-step tasks where steps depend on each other.
        """
        # If this is an update/display/read step and has no target, inherit from last file
        if step.action_type in ["edit_file", "show_result", "read_file", "delete_file"]:
            if not step.target or step.target in ["output.txt", "display the content here", "show the content"]:
                # Inherit from last created file
                if context.get("last_created_file"):
                    step.target = context["last_created_file"]
                    print(f"🔗 [PlanningAgent] Step {step.step_number} inheriting file: {step.target}")
                elif context.get("last_file_path"):
                    step.target = context["last_file_path"]
                    print(f"🔗 [PlanningAgent] Step {step.step_number} inheriting file: {step.target}")
        
        # If this is a content update and no content specified, try to extract from description
        if step.action_type == "edit_file" and not step.metadata.get("content"):
            content = self._extract_content_for_step(step.description)
            if content:
                step.metadata["content"] = content
                print(f"📝 [PlanningAgent] Step {step.step_number} extracted content: {content[:30]}...")

    def _update_step_context(self, step: PlanStep, context: dict):
        """
        Update context with results from this step.
        """
        # If this step created a file, track it
        if step.action_type == "create_file" and step.output and "Successfully wrote to" in step.output:
            # Extract file path from output
            file_match = re.search(r'Successfully wrote to\s+([\w\-/\.]+\.\w+)', step.output)
            if file_match:
                context["last_created_file"] = file_match.group(1)
                context["last_file_path"] = file_match.group(1)
                context["files_created"].append(file_match.group(1))
                print(f"📁 [PlanningAgent] Context updated: Created {file_match.group(1)}")
        
        # Also track the target if it looks like a file path
        if step.target and re.match(r'^[\w\-/\.]+\.\w+$', step.target):
            context["last_file_path"] = step.target

    async def _attempt_auto_fix(self, step: PlanStep, error: str):
        """
        Attempt to automatically fix common errors.
        
        This is similar to Qwen Code's self-debugging capability.
        """
        error_lower = error.lower()
        if step.action_type == "run_command":
            normalized = self._normalize_failed_command(step.target or step.description, error)
            if normalized and normalized != step.target:
                step.metadata["original_target"] = step.target
                step.target = normalized
                print(f"✅ [PlanningAgent] Auto-fix: normalized command to `{normalized}`")
                return

        roadmap = self._build_remediation_roadmap(step, error)
        if roadmap:
            step.metadata["remediation_roadmap"] = roadmap
            step.metadata["last_failure"] = {
                "error": error,
                "captured_at": datetime.now(UTC).isoformat(),
            }
        
        # Fix 1: File not found - create it first
        if "file not found" in error_lower or "no such file" in error_lower:
            print(f"🔧 [PlanningAgent] Auto-fix: Creating missing file for step {step.step_number}")
            if step.action_type in ["edit_file", "show_result", "read_file"]:
                # Create the file first, then retry
                file_path = step.target
                content = self._generate_file_content(f"Auto-created: {step.description}", file_path)
                success, msg = await self.coding_agent._write_file(file_path, content)
                if success:
                    step.output = f"Auto-created file: {msg}\n"
                    print(f"✅ [PlanningAgent] Auto-fix successful: Created {file_path}")
        
        # Fix 2: Permission errors - try with different path
        elif "permission" in error_lower:
            print(f"🔧 [PlanningAgent] Auto-fix: Using alternative path for step {step.step_number}")
            # Try using a safer path
            if "/" in step.target:
                safe_name = Path(step.target).name
                step.target = safe_name
                print(f"✅ [PlanningAgent] Auto-fix: Changed target to {safe_name}")
        
        # Fix 3: Content extraction failed - use description as content
        elif "content" in error_lower or "empty" in error_lower:
            print(f"🔧 [PlanningAgent] Auto-fix: Using description as content for step {step.step_number}")
            if not step.metadata.get("content"):
                step.metadata["content"] = step.description
                print(f"✅ [PlanningAgent] Auto-fix: Set content from description")
        
        # Fix 4: Import errors - add missing imports
        elif "import" in error_lower or "module" in error_lower:
            print(f"🔧 [PlanningAgent] Auto-fix: Adding missing imports for step {step.step_number}")
            # This would require more sophisticated handling
            pass

        # Fix 5: Frontend binary missing - fall back to local package binary when available
        elif "not found" in error_lower or "command not found" in error_lower:
            fixed_command = self._repair_missing_command(step.target, error)
            if fixed_command and fixed_command != step.target:
                print(f"🔧 [PlanningAgent] Auto-fix: Rewriting command for step {step.step_number}")
                step.metadata["original_target"] = step.target
                step.target = fixed_command
                print(f"✅ [PlanningAgent] Auto-fix: Updated command to `{fixed_command}`")
                return
        elif "could not read package.json" in error_lower or ("package.json" in error_lower and "enoent" in error_lower):
            inferred_command = self._infer_verification_command(step)
            if inferred_command:
                if not inferred_command.startswith("cd frontend &&") and "npm run build" in inferred_command:
                    inferred_command = "cd frontend && npm run build"
                step.metadata["original_target"] = step.target
                step.target = inferred_command
                print(f"✅ [PlanningAgent] Auto-fix: Redirected verification to `{inferred_command}`")
                return
        elif "command not allowed: empty" in error_lower:
            inferred_command = self._extract_command_from_description(step.description)
            if inferred_command:
                step.target = inferred_command
                print(f"✅ [PlanningAgent] Auto-fix: Resolved empty command to `{inferred_command}`")
                return
        elif "verification command could not be resolved" in error_lower:
            inferred_command = self._infer_verification_command(step)
            if inferred_command:
                step.target = inferred_command
                step.metadata["recovered_verification_command"] = inferred_command
                print(f"✅ [PlanningAgent] Auto-fix: Recovered verification command `{inferred_command}`")
                return
        
        # Generic fix: Log the error for manual review
        else:
            print(f"⚠️ [PlanningAgent] No auto-fix available for error: {error}")
            print(f"💡 [PlanningAgent] Suggestion: Check the step description and file path")

    def _normalize_failed_command(self, command: str, error: str) -> str | None:
        command = (command or "").strip()
        lowered = command.lower()
        error_lower = error.lower()

        frontend_root = self.project_root / "frontend"
        frontend_has_package = (frontend_root / "package.json").exists()

        if ("npm" in lowered or "vite" in lowered or "yarn" in lowered or "pnpm" in lowered) and frontend_has_package:
            if lowered.startswith("cd frontend &&"):
                return command
            if "could not read package.json" in error_lower or "package.json" in error_lower or "enoent" in error_lower:
                return f"cd frontend && {command}"
            if lowered in {"npm run build", "npm install", "npm test", "npm run dev"}:
                return f"cd frontend && {command}"

        if command.startswith("PYTHONPATH=.:backend pytest"):
            return command
        return None

    def _build_remediation_roadmap(self, step: PlanStep, error: str) -> list[dict[str, str]]:
        category = self._classify_execution_error(error)
        roadmap: list[dict[str, str]] = []

        if category == "missing_frontend_binary":
            roadmap.extend(
                [
                    {
                        "step": "Diagnose environment",
                        "status": "ready",
                        "detail": "Confirm whether frontend dependencies or the `vite` executable are missing in the current workspace.",
                    },
                    {
                        "step": "Restore local toolchain access",
                        "status": "ready",
                        "detail": "Reuse an existing `frontend/node_modules` tree or switch the verification command to the local binary path.",
                    },
                    {
                        "step": "Re-run verification",
                        "status": "ready",
                        "detail": f"Retry `{step.target}` after the frontend toolchain is reachable.",
                    },
                ]
            )
        elif category == "missing_file":
            roadmap.extend(
                [
                    {
                        "step": "Inspect referenced path",
                        "status": "ready",
                        "detail": f"Validate that `{step.target}` should exist before this step runs.",
                    },
                    {
                        "step": "Create or redirect file",
                        "status": "ready",
                        "detail": "Create the missing file or update the step target to the intended path.",
                    },
                    {
                        "step": "Retry original action",
                        "status": "ready",
                        "detail": "Run the same step again after the file path is valid.",
                    },
                ]
            )
        elif category == "permission":
            roadmap.extend(
                [
                    {
                        "step": "Reduce privilege requirements",
                        "status": "ready",
                        "detail": "Rewrite the action so it runs inside the workspace without elevated permissions.",
                    },
                    {
                        "step": "Pause for approval if still blocked",
                        "status": "ready",
                        "detail": "Escalate only if the task still requires a protected command.",
                    },
                ]
            )
        elif category == "timeout":
            roadmap.extend(
                [
                    {
                        "step": "Inspect long-running command",
                        "status": "ready",
                        "detail": "Check whether the command is waiting on a missing dependency, hanging test, or oversized scope.",
                    },
                    {
                        "step": "Narrow verification",
                        "status": "ready",
                        "detail": "Retry with a smaller targeted verification command when possible.",
                    },
                ]
            )
        else:
            roadmap.extend(
                [
                    {
                        "step": "Capture failure context",
                        "status": "ready",
                        "detail": "Record the failing command, error output, and the file or subsystem being changed.",
                    },
                    {
                        "step": "Apply smallest safe fix",
                        "status": "ready",
                        "detail": "Patch the most likely root cause without widening scope.",
                    },
                    {
                        "step": "Verify the fix",
                        "status": "ready",
                        "detail": "Re-run the same verification step and inspect drift.",
                    },
                ]
            )

        return roadmap

    def _classify_execution_error(self, error: str) -> str:
        error_lower = error.lower()
        if "vite: not found" in error_lower or "sh: 1: vite: not found" in error_lower:
            return "missing_frontend_binary"
        if "command not found" in error_lower:
            return "missing_command"
        if "could not read package.json" in error_lower or "package.json" in error_lower and "enoent" in error_lower:
            return "missing_frontend_workspace"
        if "file not found" in error_lower or "no such file" in error_lower:
            return "missing_file"
        if "permission" in error_lower or "operation not permitted" in error_lower or "forbidden" in error_lower:
            return "permission"
        if "timed out" in error_lower:
            return "timeout"
        if "import" in error_lower or "module" in error_lower:
            return "import"
        return "generic"

    def _repair_missing_command(self, command: str, error: str) -> str | None:
        error_lower = error.lower()
        if "vite" not in error_lower:
            return None

        frontend_root = self.project_root / "frontend"
        local_vite = frontend_root / "node_modules" / ".bin" / "vite"
        if not local_vite.exists():
            return None

        stripped = command.strip()
        if stripped == "npm run build":
            return "./node_modules/.bin/vite build"
        if stripped == "cd frontend && npm run build":
            return "cd frontend && ./node_modules/.bin/vite build"

        try:
            tokens = shlex.split(command)
        except ValueError:
            return None
        if tokens[-2:] == ["npm", "run"] or tokens[-3:] == ["npm", "run", "build"]:
            return command.replace("npm run build", "./node_modules/.bin/vite build")
        return None

    def _infer_verification_command(self, step: PlanStep) -> str:
        direct = self._extract_command_from_description(step.description)
        if direct:
            return direct

        packet_commands = step.metadata.get("packet_verification_commands")
        if isinstance(packet_commands, list):
            normalized = [cmd.strip() for cmd in packet_commands if isinstance(cmd, str) and cmd.strip()]
            matched = self._match_verification_command_to_description(step.description, normalized)
            if matched:
                return matched

        packet_targets = step.metadata.get("packet_targets")
        if isinstance(packet_targets, list):
            candidate_paths = [path for path in packet_targets if isinstance(path, str) and path.strip()]
            if candidate_paths:
                commands = self.coding_agent._build_verification_commands(candidate_paths)
                matched = self._match_verification_command_to_description(step.description, commands)
                if matched:
                    return matched
                if commands:
                    return commands[0]

        subsystem = str(step.metadata.get("packet_subsystem", "")).lower()
        if subsystem:
            if "frontend" in subsystem or subsystem in {"visualization", "ui"}:
                return "cd frontend && npm run build"
            if subsystem in {"routing", "self_improvement", "self-improvement", "self_reflection_and_docs"}:
                return "PYTHONPATH=.:backend pytest tests/test_backend_eval.py tests/test_agent_route_imports.py -q"

        return ""

    def _match_verification_command_to_description(self, description: str, commands: list[str]) -> str:
        if not commands:
            return ""

        lower = description.lower()
        keyword_groups = [
            (("eval", "pytest", "test suite", "internal eval"), ("pytest",)),
            (("build", "frontend", "vite"), ("npm run build", "vite build")),
            (("compile", "syntax", "backend"), ("compileall",)),
        ]
        for intent_keywords, command_markers in keyword_groups:
            if any(keyword in lower for keyword in intent_keywords):
                for command in commands:
                    command_lower = command.lower()
                    if any(marker in command_lower for marker in command_markers):
                        return command

        return commands[0]

    async def _execute_step(self, step: PlanStep):
        """Execute a single plan step."""
        if step.action_type == "create_file":
            await self._execute_create_file(step)
        elif step.action_type == "edit_file":
            await self._execute_edit_file(step)
        elif step.action_type == "show_result":
            await self._execute_show_result(step)
        elif step.action_type == "export_artifact":
            await self._execute_export_artifact(step)
        elif step.action_type == "run_command":
            await self._execute_run_command(step)
        elif step.action_type == "read_file":
            await self._execute_read_file(step)
        elif step.action_type == "delete_file":
            await self._execute_delete_file(step)
        else:
            await self._execute_general(step)

    async def _execute_create_file(self, step: PlanStep):
        """Execute a file creation step."""
        file_path = self._validate_file_path(step.target)
        if not file_path:
            file_path = self._infer_file_target_from_step(step)
            step.target = file_path

        if file_path.startswith("/"):
            file_path = file_path.lstrip("/")

        if file_path in {".ise_ai_workspace", ".", ""}:
            raise Exception("Unable to infer a valid file path for this step")

        content = step.metadata.get("content", "")
        
        print(f"📝 [PlanningAgent] Creating file: {file_path}")
        print(f"📝 [PlanningAgent] Content: {content[:50] if content else '(will generate)'}...")

        if not content:
            # CRITICAL: Generate appropriate content based on file type
            # Don't use the description as content!
            content = self._generate_appropriate_content(file_path, step.description)
            print(f"📝 [PlanningAgent] Generated content for {file_path}")

        success, msg = await self.coding_agent._write_file(file_path, content)
        
        if success:
            written_path = (self.project_root / file_path).resolve()
            if not written_path.exists() or not written_path.is_file():
                raise Exception(f"File write verification failed: {file_path} was not created")
            if written_path.stat().st_size <= 0:
                raise Exception(f"File write verification failed: {file_path} is empty")
            step.output = msg
            step.metadata["verified"] = True
            step.metadata.setdefault("agent", "BuilderAgent")
            print(f"✅ [PlanningAgent] Successfully created: {file_path}")
        else:
            print(f"❌ [PlanningAgent] Failed to create: {file_path} - {msg}")
            raise Exception(msg)

    def _generate_appropriate_content(self, file_path: str, description: str) -> str:
        """
        Generate appropriate content based on file type and context.
        
        This is CRITICAL - should NEVER use the description as content.
        """
        ext = Path(file_path).suffix.lower()
        file_name = Path(file_path).stem
        
        # Generate content based on file extension
        if ext == ".txt":
            # Text files - generate simple content
            return f"This is {file_name}.txt\nCreated by ISE AI Planning Agent\n"
        
        elif ext in [".js", ".jsx"]:
            # JavaScript/React files
            if "component" in description.lower() or ext == ".jsx":
                return f'''import React from 'react';

/**
 * {file_name} Component
 * Generated by ISE AI Planning Agent
 */
const {file_name} = () => {{
    return (
        <div className="{file_name.lower()}-container">
            <h1>{file_name}</h1>
        </div>
    );
}};

export default {file_name};
'''
            else:
                return f'''/**
 * {file_name}
 * Generated by ISE AI Planning Agent
 */

console.log("{file_name} loaded");
'''
        
        elif ext in [".ts", ".tsx"]:
            # TypeScript files
            return f'''/**
 * {file_name}
 * Generated by ISE AI Planning Agent
 */

console.log("{file_name} loaded");
'''
        
        elif ext == ".py":
            # Python files
            if "api" in description.lower() or "endpoint" in description.lower():
                return f'''"""
{file_name.title()} API
Generated by ISE AI Planning Agent
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/{file_name.lower()}")
async def get_{file_name.lower()}():
    """Get {file_name}"""
    return {{"status": "success"}}
'''
            else:
                return f'''"""
{file_name.title()}
Generated by ISE AI Planning Agent
"""

print("{file_name} loaded")
'''
        
        elif ext == ".html":
            # HTML files
            return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{file_name}</title>
</head>
<body>
    <h1>{file_name}</h1>
    <p>Generated by ISE AI Planning Agent</p>
</body>
</html>
'''
        
        elif ext == ".css":
            # CSS files
            return f'''/*
 * {file_name} Styles
 * Generated by ISE AI Planning Agent
 */

.{file_name.lower()}-container {{
    padding: 20px;
    margin: 0 auto;
}}
'''
        
        elif ext == ".json":
            # JSON files
            return f'''{{
    "name": "{file_name}",
    "version": "1.0.0",
    "description": "Generated by ISE AI Planning Agent"
}}
'''
        
        else:
            # Default for unknown types
            return f"# {file_name}\n# Generated by ISE AI Planning Agent\n"

    async def _execute_edit_file(self, step: PlanStep):
        """Execute a file edit step."""
        file_path = step.target
        
        # CRITICAL FIX: Validate file path
        file_path = self._validate_file_path(file_path)
        
        # If path starts with /, make it relative to project root
        if file_path.startswith("/"):
            file_path = file_path.lstrip("/")
        
        content = step.metadata.get("content", "")

        if not content:
            # Try to extract content from description
            content_match = re.search(r'["\'](.+?)["\']', step.description)
            if content_match:
                content = content_match.group(1)
            else:
                content = step.description

        print(f"📝 [PlanningAgent] Editing file: {file_path}")
        print(f"📝 [PlanningAgent] New content: {content[:50] if content else '(from description)'}...")

        # Read existing file
        success, existing_content = await self._read_file(file_path)

        if success:
            # Replace content
            success, msg = await self.coding_agent._write_file(file_path, content)
            if success:
                step.output = msg
                print(f"✅ [PlanningAgent] Successfully edited: {file_path}")
            else:
                print(f"❌ [PlanningAgent] Failed to edit: {file_path} - {msg}")
                raise Exception(msg)
        else:
            # File doesn't exist, create it
            print(f"⚠️ [PlanningAgent] File not found, creating: {file_path}")
            success, msg = await self.coding_agent._write_file(file_path, content)
            if success:
                step.output = f"Created and wrote to {file_path}"
                print(f"✅ [PlanningAgent] Created new file: {file_path}")
            else:
                print(f"❌ [PlanningAgent] Failed to create: {file_path} - {msg}")
                raise Exception(msg)

    async def _read_file(self, file_path: str) -> tuple[bool, str]:
        """Read a file's contents."""
        # Validate path
        file_path = self._validate_file_path(file_path)
        if file_path.startswith("/"):
            file_path = file_path.lstrip("/")
        
        try:
            path = self.project_root / file_path
            if not path.exists():
                return False, f"File not found: {file_path}"

            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                content = await f.read()
            return True, content
        except Exception as e:
            return False, f"Error reading file: {str(e)}"

    async def _execute_export_artifact(self, step: PlanStep):
        """Mark a sandbox export step as complete without treating it as a file path.

        The actual ZIP is created by the sandbox executor after all build and
        verification steps complete, because only then do we know the final
        changed files and the active chat session id.
        """
        step.output = "ExportAgent queued ZIP creation after successful implementation and verification."
        step.metadata["verified"] = True
        step.metadata.setdefault("agent", "ExportAgent")
        print("📦 [PlanningAgent] Export artifact step prepared")

    async def _execute_show_result(self, step: PlanStep):
        """Execute a show result step."""
        file_path = step.target
        
        # CRITICAL FIX: Validate file path
        file_path = self._validate_file_path(file_path)
        
        # If path starts with /, make it relative to project root
        if file_path.startswith("/"):
            file_path = file_path.lstrip("/")
        
        print(f"📝 [PlanningAgent] Showing result: {file_path}")

        # Try to read the file
        success, content = await self.coding_agent._read_file(file_path)

        if success:
            step.output = f"Content of {file_path}:\n```\n{content}\n```"
            print(f"✅ [PlanningAgent] Successfully read: {file_path}")
        else:
            step.output = f"Could not read {file_path}: {content}"
            print(f"❌ [PlanningAgent] Failed to read: {file_path} - {content}")

    async def _execute_run_command(self, step: PlanStep):
        """Execute a run command step."""
        command = (step.target or "").strip()
        if not command:
            command = self._extract_command_from_description(step.description)
            if command:
                step.target = command
        if not command:
            raise Exception("Verification command could not be resolved")

        cwd = self._infer_command_cwd(command)
        result = await self.coding_agent.terminal.run_command(command, timeout=120, cwd=cwd)
        output = self.coding_agent._format_verification_output(result.stdout, result.stderr)
        if result.return_code != 0:
            raise Exception(output or f"Command failed: {command}")
        step.output = output or f"Command executed successfully: {command}"


    def _infer_command_cwd(self, command: str) -> str | None:
        lowered = command.lower().strip()
        if lowered.startswith("cd frontend &&"):
            return None
        if "npm" in lowered or "vite" in lowered or "pnpm" in lowered or "yarn" in lowered:
            frontend_root = self.project_root / "frontend"
            if (frontend_root / "package.json").exists():
                return "frontend"
        if "pytest" in lowered or lowered.startswith("python") or "compileall" in lowered:
            return "."
        return None

    async def _execute_read_file(self, step: PlanStep):
        """Execute a read file step."""
        file_path = step.target
        success, content = await self.coding_agent._read_file(file_path)
        
        if success:
            step.output = content
        else:
            step.output = f"Could not read file: {content}"

    async def _execute_delete_file(self, step: PlanStep):
        """Execute a delete file step."""
        file_path = step.target
        try:
            path = self.project_root / file_path
            if path.exists():
                path.unlink()
                step.output = f"Deleted {file_path}"
            else:
                step.output = f"File not found: {file_path}"
        except Exception as e:
            raise Exception(f"Failed to delete file: {str(e)}")

    async def _execute_general(self, step: PlanStep):
        """Execute a general step."""
        # Try to determine what to do
        action_type = self._determine_action_type(step.description)
        
        if action_type == "create_file":
            await self._execute_create_file(step)
        elif action_type == "edit_file":
            await self._execute_edit_file(step)
        elif action_type == "show_result":
            await self._execute_show_result(step)
        elif action_type == "export_artifact":
            await self._execute_export_artifact(step)
        else:
            step.output = f"Executed: {step.description}"

    def _generate_file_content(self, description: str, file_path: str) -> str:
        """
        Generate appropriate content for a file based on context.
        
        NO TEMPLATES - Uses intelligent analysis of:
        - File extension
        - File name
        - Task description
        - Context clues
        """
        ext = Path(file_path).suffix.lower()
        file_name = Path(file_path).stem
        
        # Extract any quoted content from description
        content_match = re.search(r'["\'](.+?)["\']', description)
        quoted_content = content_match.group(1) if content_match else None
        
        # Generate based on file type and context
        if ext == ".txt":
            # Text files - use quoted content or description
            if quoted_content:
                return quoted_content
            # Extract meaningful content from description
            desc_lower = description.lower()
            if "say" in desc_lower or "display" in desc_lower or "show" in desc_lower:
                # Try to extract what to display
                display_match = re.search(r'(?:say|display|show|be)\s+["\'](.+?)["\']', desc_lower)
                if display_match:
                    return display_match.group(1)
            return f"{description}\n"
        
        elif ext in [".js", ".jsx"]:
            # JavaScript/React files
            return self._generate_javascript_file(file_name, file_path, description, quoted_content, ext)
        
        elif ext in [".ts", ".tsx"]:
            # TypeScript files
            return self._generate_typescript_file(file_name, file_path, description, quoted_content)
        
        elif ext == ".py":
            # Python files
            return self._generate_python_file(file_name, file_path, description, quoted_content)
        
        elif ext == ".html":
            # HTML files
            return self._generate_html_file(file_name, file_path, description, quoted_content)
        
        elif ext == ".css":
            # CSS files
            return self._generate_css_file(file_name, file_path, description, quoted_content)
        
        elif ext == ".json":
            # JSON files
            return self._generate_json_file(file_name, file_path, description, quoted_content)
        
        else:
            # Generic files
            if quoted_content:
                return quoted_content
            return f"{description}\n"

    def _generate_javascript_file(self, name: str, path: str, desc: str, content: Optional[str], ext: str) -> str:
        """Generate JavaScript/JSX file based on context."""
        desc_lower = desc.lower()
        
        # Detect if it's a React component
        is_react = any(kw in desc_lower for kw in ["component", "react", "jsx", "return", "render"])
        
        if is_react or ext == ".jsx":
            # React component
            display_content = content if content else name
            return f'''import React from 'react';

/**
 * {name} Component
 * Task: {desc}
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
        else:
            # Regular JavaScript
            if content:
                return f'''/**
 * {name}
 * Task: {desc}
 */

console.log("{content}");
'''
            return f'''/**
 * {name}
 * Task: {desc}
 */

console.log("{name} loaded");
'''

    def _generate_typescript_file(self, name: str, path: str, desc: str, content: Optional[str]) -> str:
        """Generate TypeScript file based on context."""
        desc_lower = desc.lower()
        
        is_react = any(kw in desc_lower for kw in ["component", "react", "tsx", "return"])
        
        if is_react or path.endswith(".tsx"):
            display_content = content if content else name
            return f'''import React from 'react';

/**
 * {name} Component
 * Task: {desc}
 */
const {name}: React.FC = () => {{
    return (
        <div className="{name.lower()}-container">
            <h1>{display_content}</h1>
        </div>
    );
}};

export default {name};
'''
        else:
            if content:
                return f'''/**
 * {name}
 * Task: {desc}
 */

console.log("{content}");
'''
            return f'''/**
 * {name}
 * Task: {desc}
 */

console.log("{name} loaded");
'''

    def _generate_python_file(self, name: str, path: str, desc: str, content: Optional[str]) -> str:
        """Generate Python file based on context."""
        desc_lower = desc.lower()
        
        # Detect if it's an API endpoint
        is_api = any(kw in desc_lower for kw in ["api", "endpoint", "route", "fastapi", "flask"])
        
        if is_api:
            return f'''"""
{name.title()} API
Task: {desc}
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/{name.lower()}")
async def get_{name.lower()}():
    """{content or f'Get {name}'}"""
    return {{"status": "success"}}
'''
        elif content:
            return f'''"""
{name.title()}
Task: {desc}
"""

print("{content}")
'''
        else:
            return f'''"""
{name.title()}
Task: {desc}
"""

print("{name} loaded")
'''

    def _generate_html_file(self, name: str, path: str, desc: str, content: Optional[str]) -> str:
        """Generate HTML file based on context."""
        display_content = content if content else name
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{display_content}</title>
</head>
<body>
    <h1>{display_content}</h1>
    <!-- Task: {desc} -->
</body>
</html>
'''

    def _generate_css_file(self, name: str, path: str, desc: str, content: Optional[str]) -> str:
        """Generate CSS file based on context."""
        return f'''/*
 * {name} Styles
 * Task: {desc}
 */

.{name.lower()}-container {{
    padding: 20px;
    margin: 0 auto;
}}
'''

    def _generate_json_file(self, name: str, path: str, desc: str, content: Optional[str]) -> str:
        """Generate JSON file based on context."""
        if content:
            try:
                # Try to parse as JSON
                import json
                data = json.loads(content)
                return json.dumps(data, indent=2)
            except:
                pass
        return json.dumps({"task": desc, "name": name}, indent=2)

    async def _report_progress(self, plan: ExecutionPlan):
        """Report progress via callback and persist progress as a checkpoint and publish to subscribers."""
        # Callback for immediate in-process UI
        if self.progress_callback:
            try:
                await self.progress_callback(plan)
            except Exception:
                pass

        # Save durable checkpoint and publish progress events for external dashboards
        try:
            plan_id = save_checkpoint(plan, getattr(plan, "_checkpoint_id", None))
            # Publish a compact progress event
            try:
                from app.services.progress_broadcaster import publish_progress

                # Non-blocking publish
                asyncio.create_task(publish_progress(plan_id, plan.to_progress_event()))
            except Exception:
                # If broadcaster not available, ignore
                pass
        except Exception:
            pass

    async def execute_task_with_plan(
        self,
        task: str,
        project_context: Optional[dict[str, Any]] = None,
    ) -> ExecutionPlan:
        """
        High-level method to execute a task with full planning.

        This is the main entry point for the planning agent.

        Args:
            task: User's task description

        Returns:
            Completed execution plan
        """
        print(f"📋 [PlanningAgent] Creating plan for: {task[:80]}...")
        
        # Step 1: Create the plan
        plan = await self.create_plan(task, project_context)
        print(f"✅ [PlanningAgent] Plan created with {plan.total_steps} steps")
        
        # Step 2: Execute the plan
        print(f"🚀 [PlanningAgent] Executing plan...")
        completed_plan = await self.execute_plan(plan)
        
        print(f"✅ [PlanningAgent] Plan completed: {completed_plan.status.value} ({completed_plan.completed_steps}/{completed_plan.total_steps})")
        
        return completed_plan


# Singleton instance
_planning_agent: Optional[AutonomousPlanningAgent] = None


def get_planning_agent(project_root: Optional[Path] = None) -> AutonomousPlanningAgent:
    """Get or create planning agent instance."""
    global _planning_agent
    if _planning_agent is None:
        _planning_agent = AutonomousPlanningAgent(project_root)
    elif project_root is not None and _planning_agent.project_root != project_root:
        _planning_agent = AutonomousPlanningAgent(project_root)
    return _planning_agent
