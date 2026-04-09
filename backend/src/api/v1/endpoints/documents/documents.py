from fastapi import APIRouter, Depends, HTTPException

from src.api.v1.endpoints.auth.deps import get_current_admin, get_current_user
from src.api.v1.endpoints.documents.deps import get_documents_service
from src.api.v1.endpoints.documents.schemas import ChunkResponse, IngestRequest, IngestResponse
from src.application.documents.dto.ingest_dto import IngestDocumentsCommand
from src.application.documents.services.documents_application_service import (
    DocumentsApplicationService,
)
from src.domain.auth.entities.user import User

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_documents(
    request: IngestRequest,
    admin: User = Depends(get_current_admin),
    service: DocumentsApplicationService = Depends(get_documents_service),
) -> IngestResponse:
    """Trigger document ingestion from a parquet source file."""
    command = IngestDocumentsCommand(
        source_path=request.source_path,
        heritage_type=request.heritage_type,
        chunk_size=request.chunk_size,
        chunk_overlap=request.chunk_overlap,
    )
    result = await service.ingest_documents(command)
    return IngestResponse(
        total_documents=result.total_documents,
        total_chunks=result.total_chunks,
        skipped_chunks=result.skipped_chunks,
        message=(
            f"Ingestion complete: {result.total_documents} documents processed, "
            f"{result.total_chunks} new chunks created, "
            f"{result.skipped_chunks} chunks skipped (already existed)."
        ),
    )


@router.get("/chunks/{document_id}", response_model=list[ChunkResponse])
async def get_document_chunks(
    document_id: str,
    user: User = Depends(get_current_user),
    service: DocumentsApplicationService = Depends(get_documents_service),
) -> list[ChunkResponse]:
    """List all chunks for a given document (useful for debugging)."""
    chunks = await service.get_chunks_by_document(document_id)
    if not chunks:
        raise HTTPException(status_code=404, detail="No chunks found for this document")
    return [
        ChunkResponse(
            id=str(chunk.id),
            document_id=chunk.document_id,
            content=chunk.content,
            chunk_index=chunk.chunk_index,
            token_count=chunk.token_count,
        )
        for chunk in chunks
    ]
