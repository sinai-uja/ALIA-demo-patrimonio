from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The user question about Andalusian heritage")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")
    heritage_type_filter: str | None = Field(
        default=None, description="Filter by heritage type (e.g. BIC, Monumento)"
    )
    province_filter: str | None = Field(
        default=None, description="Filter by Andalusian province"
    )


class SourceSchema(BaseModel):
    title: str
    url: str
    score: float
    heritage_type: str
    province: str
    municipality: str | None = None
    metadata: dict | None = None


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceSchema]
    query: str
    abstained: bool = False
