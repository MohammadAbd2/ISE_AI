from __future__ import annotations
import re
from dataclasses import asdict, dataclass
from typing import Any
from uuid import uuid4

@dataclass(slots=True)
class PlanCandidate:
    id: str; strategy: str; steps: list[dict[str, Any]]; score: int; rationale: str
    def to_dict(self) -> dict[str, Any]: return asdict(self)
class TreeOfThoughtPlanner:
    def generate_candidates(self, task: str) -> list[PlanCandidate]:
        t=task.lower(); domain=self.extract_domain(task); c=[]
        wants_app=any(k in t for k in ['landing page','website','dashboard','cms','app'])
        wants_component='component' in t and not wants_app
        if wants_component:
            c.append(PlanCandidate(str(uuid4()), 'focused-component', [
                {'agent':'PlannerAgent','action':'design','detail':f'Extract component requirements for {domain}'},
                {'agent':'BuilderAgent','action':'write_file','path':'frontend/src/components/GeneratedComponent.jsx'},
                {'agent':'BuilderAgent','action':'write_file','path':'frontend/src/components/GeneratedComponent.css'},
                {'agent':'VerifierAgent','action':'build','command':'cd frontend && npm run build'},
                {'agent':'ExportAgent','action':'export','mode':'component'}], 86, 'Small scope; export only generated component files.'))
        c.append(PlanCandidate(str(uuid4()), 'modular-frontend', [
            {'agent':'PlannerAgent','action':'architecture','detail':f'Design sections and files for {domain}'},
            {'agent':'BuilderAgent','action':'write_file','path':'frontend/src/App.jsx'},
            {'agent':'BuilderAgent','action':'write_file','path':'frontend/src/App.css'},
            {'agent':'VerifierAgent','action':'build','command':'cd frontend && npm run build'},
            {'agent':'VerifierAgent','action':'preview','detail':'Start preview and run browser smoke when possible'},
            {'agent':'ExportAgent','action':'export','mode':'frontend-project'}], 92 if wants_app else 74, 'Deliverable, previewable frontend project.'))
        c.append(PlanCandidate(str(uuid4()), 'fullstack-project', [
            {'agent':'PlannerAgent','action':'architecture','detail':f'Design frontend, backend API, and data model for {domain}'},
            {'agent':'BuilderAgent','action':'write_frontend'}, {'agent':'BuilderAgent','action':'write_backend'},
            {'agent':'VerifierAgent','action':'test','command':'pytest -q'}, {'agent':'VerifierAgent','action':'build','command':'cd frontend && npm run build'},
            {'agent':'ExportAgent','action':'export','mode':'full-project'}], 88 if any(k in t for k in ['backend','node','api','cms','fullstack']) else 70, 'Use for backend/API/CMS tasks.'))
        return sorted(c, key=lambda x:x.score, reverse=True)
    def select_best(self, task: str) -> PlanCandidate: return self.generate_candidates(task)[0]
    def extract_domain(self, task: str) -> str:
        cleaned=re.sub(r'\b(create|build|make|roadmap|road map|plan|zip|downloadable|download|using|with|react|node|website|landing page|project|implement|give me|file)\b',' ',task,flags=re.I)
        return re.sub(r'\s+',' ',cleaned).strip(' .,-')[:80] or 'requested product'
_tree_planner=TreeOfThoughtPlanner()
def get_tree_planner() -> TreeOfThoughtPlanner: return _tree_planner
