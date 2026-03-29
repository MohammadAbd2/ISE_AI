from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(examples=["user", "assistant", "system"])
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation: list[ChatMessage] = Field(default_factory=list)
    model: str | None = None
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    model: str


class ModelsResponse(BaseModel):
    models: list[str]


class ChatSessionSummary(BaseModel):
    id: str
    title: str
    model: str
    updated_at: str
    preview: str


class ChatSessionDetail(BaseModel):
    id: str
    title: str
    model: str
    updated_at: str
    messages: list[ChatMessage]


class ChatSessionsResponse(BaseModel):
    sessions: list[ChatSessionSummary]
    storage_mode: str = "memory"


class AIProfileResponse(BaseModel):
    custom_instructions: str
    memory: str
    storage_mode: str


class AIProfileUpdateRequest(BaseModel):
    custom_instructions: str = ""
    memory: str = ""
