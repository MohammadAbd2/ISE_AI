from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.services.unified_execution_controller import get_unified_execution_controller

router = APIRouter(prefix="/api/unified-agent", tags=["Unified Agent v12-v20"])

class ExecuteRequest(BaseModel):
    task: str = Field(..., min_length=1)
    source_path: str | None = None
    max_attempts: int = 4

@router.get('/roadmap')
def roadmap():
    return {
        'title': 'Unified Dynamic Agent Roadmap v12-v20',
        'status': 'implemented_foundation',
        'phases': [
            {'id':'P12','name':'Unified execution brain','status':'implemented'},
            {'id':'P13','name':'Self-healing execution loop','status':'implemented'},
            {'id':'P14','name':'Dynamic output engine','status':'implemented'},
            {'id':'P15','name':'Figma/design intelligence model','status':'implemented'},
            {'id':'P16','name':'Visual Thinking DesigningAgent','status':'implemented'},
            {'id':'P17','name':'Live/static preview runtime contract','status':'implemented'},
            {'id':'P18','name':'Failure memory-ready debug model','status':'implemented'},
            {'id':'P19','name':'Chat always renders execution result','status':'implemented'},
            {'id':'P20','name':'UX/UI dynamic render blocks','status':'implemented'},
        ],
    }

@router.post('/execute')
def execute(payload: ExecuteRequest):
    return get_unified_execution_controller().run(payload.task, payload.source_path, payload.max_attempts)

@router.post('/design/prototype')
def prototype(payload: ExecuteRequest):
    return get_unified_execution_controller().run('Create a dynamic Figma-like prototype: ' + payload.task, payload.source_path, payload.max_attempts)
