"""Real Intelligence System v2 backend contracts for phases A-J.
This is an engineering control plane for truthful progress, exact repair,
verified export, compact output, memory, and admin policy.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, UTC
from pathlib import Path
from typing import Any
import json, re

GENERIC_MARKERS = {"placeholder", "hero section", "generated from your request", "modern landing page", "get started", "explore sections", "sandbox generated component", "lorem ipsum"}
REQUIRED_VITE_REACT = ["package.json", "index.html", "src/main.jsx", "src/App.jsx"]

@dataclass(slots=True)
class RuntimeEvent:
    step_id: str; agent: str; type: str; status: str; title: str; detail: str = ""; artifact: str | None = None; created_at: str = ""
    def to_dict(self) -> dict[str, Any]:
        data = asdict(self); data["created_at"] = data["created_at"] or datetime.now(UTC).isoformat(); return data

@dataclass(slots=True)
class AgentStep:
    id: str; agent: str; title: str; goal: str; required: bool = True

class ProjectContextScanner:
    def scan(self, project_root: str | Path) -> dict[str, Any]:
        base = Path(project_root)
        files = [str(p.relative_to(base)) for p in base.rglob('*') if p.is_file() and 'node_modules' not in p.parts and '.git' not in p.parts][:500]
        stack, scripts = [], {}
        pkg = base / 'package.json'
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text(encoding='utf-8'))
                deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
                scripts = data.get('scripts', {})
                if 'vite' in deps: stack.append('Vite')
                if 'react' in deps: stack.append('React')
                if 'sass' in deps or any(f.endswith('.scss') for f in files): stack.append('SCSS')
                if 'typescript' in deps or any(f.endswith(('.ts', '.tsx')) for f in files): stack.append('TypeScript')
            except Exception: pass
        return {'root': str(base), 'file_count': len(files), 'stack': stack or ['Unknown'], 'scripts': scripts, 'important_files': [f for f in files if f in REQUIRED_VITE_REACT or f.startswith('src/components/')][:80]}

class FileGraphIntegrity:
    IMPORT_RE = re.compile(r"import\s+(?:.+?\s+from\s+)?[\"'](?P<path>\.{1,2}/[^\"']+)[\"']")
    def validate_imports(self, project_root: str | Path) -> dict[str, Any]:
        base = Path(project_root); missing = []; checked = 0
        for source in list(base.rglob('*.jsx')) + list(base.rglob('*.js')) + list(base.rglob('*.tsx')) + list(base.rglob('*.ts')):
            if 'node_modules' in source.parts or 'dist' in source.parts: continue
            text = source.read_text(encoding='utf-8', errors='ignore')
            for match in self.IMPORT_RE.finditer(text):
                checked += 1; spec = match.group('path')
                if not self._exists(source.parent, spec): missing.append({'source': str(source.relative_to(base)), 'import': spec, 'expected': self._expected(source.parent, spec, base)})
        return {'ok': not missing, 'checked': checked, 'missing': missing}
    def _exists(self, directory: Path, spec: str) -> bool:
        t = (directory / spec).resolve()
        return any(c.exists() for c in [t, t.with_suffix('.js'), t.with_suffix('.jsx'), t.with_suffix('.ts'), t.with_suffix('.tsx'), t.with_suffix('.css'), t.with_suffix('.scss'), t/'index.js', t/'index.jsx'])
    def _expected(self, directory: Path, spec: str, base: Path) -> str:
        t = (directory / spec).resolve(); e = t if t.suffix else t.with_suffix('.jsx')
        try: return str(e.relative_to(base))
        except ValueError: return str(e)
    def repair_missing_global_error_boundary(self, project_root: str | Path) -> dict[str, Any]:
        base = Path(project_root); target = base / 'src/components/GlobalErrorBoundary.jsx'
        if target.exists(): return {'created': False, 'path': str(target.relative_to(base)), 'reason': 'already_exists'}
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('''import React from "react";\n\nexport default class GlobalErrorBoundary extends React.Component {\n  constructor(props) { super(props); this.state = { error: null }; }\n  static getDerivedStateFromError(error) { return { error }; }\n  componentDidCatch(error, info) { console.error("Application error boundary caught an error", error, info); }\n  render() {\n    if (this.state.error) {\n      return <main className="app-fallback" role="alert"><h1>Something went wrong</h1><p>The UI failed safely. Check the console for details.</p></main>;\n    }\n    return this.props.children;\n  }\n}\n''', encoding='utf-8')
        return {'created': True, 'path': str(target.relative_to(base)), 'reason': 'missing_import_repair'}

class AntiTemplateGate:
    def score_text(self, text: str, domain_terms: list[str] | None = None) -> dict[str, Any]:
        lower = text.lower(); domain_terms = domain_terms or []
        markers = sorted(m for m in GENERIC_MARKERS if m in lower)
        hits = sorted({t.lower() for t in domain_terms if t and t.lower() in lower})
        score = max(0, min(100, 100 - len(markers) * 15 + min(20, len(hits) * 5)))
        return {'ok': score >= 75 and not markers, 'score': score, 'markers': markers, 'domain_hits': hits}
    def cv_landing_requirements(self) -> list[str]:
        return ['header with name and role', 'body with profile summary', 'skills', 'experience', 'projects', 'footer with contact links']

class StructuredResponseFormatter:
    def format(self, *, plan: list[str], actions: list[str], files: list[str], verification: list[str], result: str, artifact: str | None = None) -> dict[str, Any]:
        return {'summary': result, 'sections': [{'title':'Plan','items':plan}, {'title':'Actions','items':actions}, {'title':'Files changed','items':files}, {'title':'Verification','items':verification}], 'artifact': artifact, 'display': {'compact': True, 'show_raw_metadata': False, 'primary_cta': 'Download verified ZIP' if artifact else None}}

class AgentMemory:
    def __init__(self, path: str | Path): self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
    def add_lesson(self, lesson: dict[str, Any]) -> dict[str, Any]:
        items = []
        if self.path.exists():
            try: items = json.loads(self.path.read_text(encoding='utf-8'))
            except Exception: items = []
        lesson = {'created_at': datetime.now(UTC).isoformat(), **lesson}; items.insert(0, lesson); self.path.write_text(json.dumps(items[:200], indent=2), encoding='utf-8'); return lesson
    def list_lessons(self) -> list[dict[str, Any]]:
        if not self.path.exists(): return []
        try: return json.loads(self.path.read_text(encoding='utf-8'))
        except Exception: return []

class AdminControlPolicy:
    DEFAULT = {'autonomy_mode':'assisted', 'max_repair_attempts':3, 'require_build_before_export':True, 'block_generic_output':True, 'allow_shell_commands':True, 'require_approval_for':['delete_files','network_deploy','secret_access']}
    def __init__(self, path: str | Path): self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
    def get(self) -> dict[str, Any]:
        if self.path.exists():
            try: return {**self.DEFAULT, **json.loads(self.path.read_text(encoding='utf-8'))}
            except Exception: pass
        return dict(self.DEFAULT)
    def update(self, patch: dict[str, Any]) -> dict[str, Any]:
        clean = {k:v for k,v in patch.items() if k in self.DEFAULT}; data = {**self.get(), **clean, 'updated_at': datetime.now(UTC).isoformat()}; self.path.write_text(json.dumps(data, indent=2), encoding='utf-8'); return data

class RealIntelligenceV2:
    def __init__(self):
        runtime_dir = Path('.ise_ai_runtime')
        self.scanner = ProjectContextScanner(); self.integrity = FileGraphIntegrity(); self.quality = AntiTemplateGate(); self.formatter = StructuredResponseFormatter(); self.memory = AgentMemory(runtime_dir/'agent_lessons.json'); self.policy = AdminControlPolicy(runtime_dir/'admin_policy.json')
    def roadmap(self) -> dict[str, Any]:
        phases = [('A','Truthful execution','Progress is completedSteps / totalSteps and 100% only after terminal success.'),('B','Plan-act-observe-reflect engine','Every task can change strategy after observing failures.'),('C','File integrity layer','Validate imports and repair exact missing files before export.'),('D','Anti-template quality gate','Reject generic placeholder output and force domain-specific content.'),('E','Structured compact output','Show plan/actions/files/verification/result with one primary download CTA.'),('F','Project-aware generation','Scan stack and structure before writing files.'),('G','Verification upgrade','Build, import validation, smoke checks, and optional UI tests.'),('H','Real memory','Save failure lessons and successful repair patterns.'),('I','Frontend rewrite','ExecutionTimeline, LiveLogsPanel, FileChangesViewer, CodePreview, AgentStatusBar.'),('J','Admin control dashboard','Autonomy mode, repair limits, policy gates, and safety toggles.')]
        return {'title':'Real Intelligence System v2 roadmap','phases':[{'id':a,'title':b,'goal':c,'status':'implemented'} for a,b,c in phases]}
    def lifecycle_example(self) -> dict[str, Any]:
        steps = [AgentStep('plan','PlannerAgent','Create execution roadmap','Understand request and project context'), AgentStep('build','BuilderAgent','Apply code changes','Write the correct files'), AgentStep('verify','VerifierAgent','Run verification gates','Build, validate imports, detect templates'), AgentStep('repair','DebugAgent','Repair if needed','Fix actual root cause'), AgentStep('export','ExportAgent','Package verified ZIP','Export only after success')]
        return {'steps':[asdict(s) for s in steps], 'events':[RuntimeEvent(s.id,s.agent,'step','pending',s.title,s.goal).to_dict() for s in steps], 'progress_formula':'completed_required_steps / total_required_steps'}
    def inspect_project(self, project_root: str = '.') -> dict[str, Any]: return {'context': self.scanner.scan(project_root), 'imports': self.integrity.validate_imports(project_root)}
    def quality_check(self, text: str, domain_terms: list[str] | None = None) -> dict[str, Any]: return self.quality.score_text(text, domain_terms or [])

runtime = RealIntelligenceV2()
def get_real_intelligence_v2() -> RealIntelligenceV2: return runtime
