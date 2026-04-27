from __future__ import annotations
import time
from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

@dataclass(slots=True)
class AutonomousProjectRun:
    id: str; prompt: str; status: str='queued'; mode: str='autonomous-project'; created_at: float=field(default_factory=time.time); controls: dict[str,bool]=field(default_factory=lambda:{'paused':False,'cancelled':False}); milestones: list[dict[str,Any]]=field(default_factory=list)
    def to_dict(self)->dict[str,Any]:
        d=asdict(self); d['elapsed_seconds']=int(time.time()-self.created_at); return d
class AutonomousProjectRegistry:
    def __init__(self): self._runs: dict[str,AutonomousProjectRun]={}
    def create(self,prompt:str)->dict[str,Any]:
        r=AutonomousProjectRun(id=str(uuid4()),prompt=prompt,status='planning'); r.milestones.append({'agent':'PlannerAgent','event':'Project mode created','status':'completed','time':0}); self._runs[r.id]=r; return r.to_dict()
    def list(self)->list[dict[str,Any]]: return [r.to_dict() for r in self._runs.values()]
    def get(self,run_id:str)->dict[str,Any]|None: return self._runs[run_id].to_dict() if run_id in self._runs else None
    def control(self,run_id:str,action:str)->dict[str,Any]:
        r=self._runs[run_id]
        if action=='pause': r.controls['paused']=True; r.status='paused'
        elif action=='resume': r.controls['paused']=False; r.status='running'
        elif action=='cancel': r.controls['cancelled']=True; r.status='cancelled'
        elif action=='force_export': r.milestones.append({'agent':'ExportAgent','event':'Force export requested','status':'queued','time':r.to_dict()['elapsed_seconds']})
        else: raise ValueError('Unsupported control action')
        return r.to_dict()
_registry=AutonomousProjectRegistry()
def get_autonomous_project_registry()->AutonomousProjectRegistry: return _registry
