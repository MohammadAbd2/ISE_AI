from __future__ import annotations
import json, time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

@dataclass(slots=True)
class ImprovementLesson:
    id: str; task: str; outcome: str; failures: list[str]=field(default_factory=list); fixes: list[str]=field(default_factory=list); recommendations: list[str]=field(default_factory=list); created_at: float=field(default_factory=time.time)
    def to_dict(self)->dict[str,Any]: return asdict(self)
class ContinuousImprovementStore:
    def __init__(self, path: str|Path|None=None):
        self.path=Path(path or Path.home()/'.cache'/'ise_ai'/'learning'/'improvements.jsonl').expanduser().resolve(); self.path.parent.mkdir(parents=True, exist_ok=True)
    def record(self, task: str, outcome: str, *, failures: list[str]|None=None, fixes: list[str]|None=None) -> ImprovementLesson:
        failures=failures or []; fixes=fixes or []; recs=[]
        if failures: recs += ['Retrieve similar failures before planning future tasks.', 'Run verification immediately after the failing step.']
        if outcome=='success': recs.append('Reuse successful architecture and export mode for similar tasks.')
        lesson=ImprovementLesson(str(uuid4()), task, outcome, failures, fixes, recs)
        with self.path.open('a',encoding='utf-8') as h: h.write(json.dumps(lesson.to_dict())+'\n')
        return lesson
    def search(self, query: str, limit: int=8) -> list[dict[str,Any]]:
        if not self.path.exists(): return []
        terms={t.lower() for t in query.split() if len(t)>2}; rows=[]
        for line in self.path.read_text(encoding='utf-8').splitlines():
            try: row=json.loads(line)
            except Exception: continue
            hay=json.dumps(row).lower(); score=sum(1 for t in terms if t in hay)
            if score: rows.append((score,row))
        rows.sort(key=lambda x:(x[0],x[1].get('created_at',0)), reverse=True)
        return [r for _,r in rows[:limit]]
_store=ContinuousImprovementStore()
def get_improvement_store() -> ContinuousImprovementStore: return _store
