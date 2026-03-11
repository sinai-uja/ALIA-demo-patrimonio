from sqlalchemy.ext.asyncio import AsyncSession

from src.application.documents.services.documents_application_service import (
    DocumentsApplicationService,
)
from src.application.documents.use_cases.ingest_documents import IngestDocumentsUseCase
from src.domain.documents.services.chunking_service import ChunkingService
from src.infrastructure.documents.adapters.embedding_adapter import HttpEmbeddingAdapter
from src.infrastructure.documents.adapters.parquet_loader import ParquetDocumentLoader
from src.infrastructure.documents.repositories.document_repository import (
    SqlAlchemyDocumentRepository,
)


def build_documents_application_service(
    db: AsyncSession,
) -> DocumentsApplicationService:
    """Wire all dependencies for the documents bounded context."""
    loader = ParquetDocumentLoader()
    embedding_adapter = HttpEmbeddingAdapter()
    repository = SqlAlchemyDocumentRepository(session=db)
    chunking_service = ChunkingService()

    ingest_use_case = IngestDocumentsUseCase(
        document_loader=loader,
        chunking_service=chunking_service,
        embedding_port=embedding_adapter,
        document_repository=repository,
    )

    return DocumentsApplicationService(
        ingest_use_case=ingest_use_case,
        document_repository=repository,
    )
