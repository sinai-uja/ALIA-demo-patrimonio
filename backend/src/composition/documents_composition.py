from sqlalchemy.ext.asyncio import AsyncSession

from src.application.documents.services.documents_application_service import (
    DocumentsApplicationService,
)
from src.application.documents.use_cases.ingest_documents import IngestDocumentsUseCase
from src.composition.token_provider_composition import build_token_provider
from src.config import settings
from src.domain.documents.services.chunking_service import ChunkingService
from src.domain.documents.services.document_enrichment_service import (
    DocumentEnrichmentService,
)
from src.infrastructure.documents.adapters.parquet_loader import ParquetDocumentLoader
from src.infrastructure.documents.repositories.document_repository import (
    SqlAlchemyDocumentRepository,
)
from src.infrastructure.shared.adapters.embedding_adapter import HttpEmbeddingAdapter
from src.infrastructure.shared.adapters.sqlalchemy_unit_of_work import (
    SqlAlchemyUnitOfWork,
)

# Module-level singletons
_loader = ParquetDocumentLoader()
_embedding_adapter = HttpEmbeddingAdapter(
    token_provider=build_token_provider(settings.embedding_service_url),
)
_chunking_service = ChunkingService()
_enrichment_service = DocumentEnrichmentService(
    chunks_version=settings.chunks_table_version,
)


def build_documents_application_service(
    db: AsyncSession,
) -> DocumentsApplicationService:
    """Wire all dependencies for the documents bounded context."""
    # Per-request (need DB session)
    repository = SqlAlchemyDocumentRepository(session=db)
    unit_of_work = SqlAlchemyUnitOfWork(session=db)

    ingest_use_case = IngestDocumentsUseCase(
        document_loader=_loader,
        chunking_service=_chunking_service,
        embedding_port=_embedding_adapter,
        document_repository=repository,
        enrichment_service=_enrichment_service,
        unit_of_work=unit_of_work,
    )

    return DocumentsApplicationService(
        ingest_use_case=ingest_use_case,
        document_repository=repository,
    )
