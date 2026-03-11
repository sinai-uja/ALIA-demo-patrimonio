from pydantic import BaseModel, Field


class SimplifyRequest(BaseModel):
    text: str = Field(
        ..., min_length=1, description="The heritage text to simplify"
    )
    level: str = Field(
        default="basic",
        description="Simplification level: 'basic' (max simplification) or 'intermediate'",
    )
    document_id: str | None = Field(
        default=None, description="Optional source document identifier"
    )


class SimplifyResponse(BaseModel):
    original_text: str
    simplified_text: str
    level: str
    document_id: str | None
