from typing import Literal

from pydantic import BaseModel, Field


class SearchSource(BaseModel):
    title: str
    url: str
    snippet: str = Field(default="", description="Short line from the search engine or a brief fallback.")
    page_excerpt: str = Field(
        default="",
        description="Longer text extracted from the page for top results when fetch succeeds.",
    )
    domain: str = ""


class WebSearchLog(BaseModel):
    query: str
    provider: str = "duckduckgo"
    status: Literal["completed", "failed"] = "completed"
    searched_at: str
    summary: str = ""
    sources: list[SearchSource] = Field(default_factory=list)
    error: str = ""


class ImageHit(BaseModel):
    """A single image result (web search) or a generated still."""

    title: str = ""
    image_url: str
    thumbnail_url: str = ""
    page_url: str = ""
    source_name: str = ""


class ImageIntelLog(BaseModel):
    """Image search or local generation bundle for one user turn."""

    kind: Literal["search", "generation"] = "search"
    query: str = ""
    provider: str = "duckduckgo-images"
    status: Literal["completed", "failed"] = "completed"
    searched_at: str = ""
    summary: str = ""
    images: list[ImageHit] = Field(default_factory=list)
    error: str = ""
    generator_model: str = ""
    vision_notes: str = Field(
        default="",
        description="Structured vision output used to build search queries.",
    )


class ChatAttachment(BaseModel):
    id: str
    name: str
    kind: str = "file"
    content_type: str = "application/octet-stream"
    size: int | None = None
    preview: str = ""


class RenderBlock(BaseModel):
    type: str
    payload: dict = Field(default_factory=dict)


class ChatMessage(BaseModel):
    """Single message exchanged between the frontend and backend."""
    role: str = Field(examples=["user", "assistant", "system"])
    content: str = Field(min_length=1)
    attachments: list[ChatAttachment] = Field(default_factory=list)
    search_logs: list[WebSearchLog] = Field(default_factory=list)
    image_logs: list[ImageIntelLog] = Field(default_factory=list)
    render_blocks: list[RenderBlock] = Field(default_factory=list)


class ChatRequest(BaseModel):
    """Incoming chat request for both regular and streaming endpoints."""
    message: str = Field(min_length=1)
    conversation: list[ChatMessage] = Field(default_factory=list)
    attachments: list[ChatAttachment] = Field(default_factory=list)
    model: str | None = None
    session_id: str | None = None
    effort: Literal["low", "medium", "high"] = "medium"
    mode: Literal["auto", "chat", "agent"] = "auto"  # Mode selection with auto-detect


class ChatResponse(BaseModel):
    """Non-streaming response payload."""
    reply: str
    model: str
    search_logs: list[WebSearchLog] = Field(default_factory=list)
    image_logs: list[ImageIntelLog] = Field(default_factory=list)
    render_blocks: list[RenderBlock] = Field(default_factory=list)


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


class FileUploadRequest(BaseModel):
    session_id: str
    filename: str
    content_type: str = "application/octet-stream"
    data_base64: str = Field(min_length=1)


class FileUploadResponse(BaseModel):
    attachment: ChatAttachment
    storage_mode: str


class ArtifactSummary(BaseModel):
    id: str
    session_id: str
    kind: str
    title: str
    preview: str = ""
    metadata: dict = Field(default_factory=dict)
    created_at: str
    updated_at: str


class ArtifactListResponse(BaseModel):
    artifacts: list[ArtifactSummary]


class SessionAnalyticsResponse(BaseModel):
    session_id: str
    visualization: dict | None = None
    render_blocks: list[RenderBlock] = Field(default_factory=list)
    artifacts: list[ArtifactSummary] = Field(default_factory=list)
    has_context: bool = False
