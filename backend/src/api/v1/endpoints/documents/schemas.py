from pydantic import BaseModel


class IngestRequest(BaseModel):
    source_path: str
    heritage_type: str
    chunk_size: int = 512
    chunk_overlap: int = 64


class IngestResponse(BaseModel):
    total_documents: int
    total_chunks: int
    skipped_chunks: int
    message: str


class ChunkResponse(BaseModel):
    id: str
    document_id: str
    content: str
    chunk_index: int
    token_count: int
