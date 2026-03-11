from src.application.documents.dto.ingest_dto import IngestDocumentsCommand, IngestResultDTO
from src.application.documents.use_cases.ingest_documents import IngestDocumentsUseCase
from src.domain.documents.entities.chunk import Chunk
from src.domain.documents.ports.document_repository import DocumentRepository


class DocumentsApplicationService:
    """Application service that exposes document operations to the API layer."""

    def __init__(
        self,
        ingest_use_case: IngestDocumentsUseCase,
        document_repository: DocumentRepository,
    ) -> None:
        self._ingest_use_case = ingest_use_case
        self._document_repository = document_repository

    async def ingest_documents(self, command: IngestDocumentsCommand) -> IngestResultDTO:
        return await self._ingest_use_case.execute(command)

    async def get_chunks_by_document(self, document_id: str) -> list[Chunk]:
        return await self._document_repository.get_chunks_by_document(document_id)
