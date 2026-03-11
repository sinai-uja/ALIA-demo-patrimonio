from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    title: str = Field(default="Nueva conversación", description="Session title")


class SessionResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, description="The user message text")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")
    heritage_type_filter: str | None = Field(
        default=None, description="Filter by heritage type"
    )
    province_filter: str | None = Field(
        default=None, description="Filter by Andalusian province"
    )


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    sources: list[dict]
    created_at: str
