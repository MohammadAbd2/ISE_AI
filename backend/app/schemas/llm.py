from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class LLMPlanStep(BaseModel):
    description: str = Field(..., min_length=3)
    action_type: Optional[str]
    target: Optional[str]
    metadata: Optional[Dict[str, Any]] = {}
