from sqlalchemy.ext.asyncio import AsyncSession

from src.application.documents.services.documents_application_service import (
    DocumentsApplicationService,
)
from src.application.documents.use_cases.ingest_documents import IngestDocumentsUseCase
from src.composition.token_provider_composition import build_token_provider
from src.config import settings
from src.domain.documents.ports.document_loader import DocumentLoader
from src.domain.documents.services.chunking_service import ChunkingService
from src.domain.documents.services.document_enrichment_service import (
    DocumentEnrichmentService,
)
from src.infrastructure.documents.adapters.jsonl_loader import JsonlDocumentLoader
from src.infrastructure.documents.adapters.parquet_loader import ParquetDocumentLoader
from src.infrastructure.documents.repositories.document_repository import (
    SqlAlchemyDocumentRepository,
)
from src.infrastructure.shared.adapters.embedding_adapter import HttpEmbeddingAdapter
from src.infrastructure.shared.adapters.sqlalchemy_unit_of_work import (
    SqlAlchemyUnitOfWork,
)


def _select_loader(chunks_version: str) -> DocumentLoader:
    """Pick the document loader implementation for the active schema.

    - ``v6``: new IAPH JSONL format from Samuel/UJA
    - any other version: legacy parquet datasets
    """
    if chunks_version == "v6":
        return JsonlDocumentLoader()
    return ParquetDocumentLoader()


# Module-level singletons
_loader = _select_loader(settings.chunks_table_version)
_embedding_adapter = HttpEmbeddingAdapter(
    token_provider=build_token_provider(settings.embedding_service_url),
)
_chunking_service = ChunkingService()
_enrichment_service = DocumentEnrichmentService(
    chunks_version=settings.chunks_table_version,
)


def build_documents_application_service(
    db: AsyncSession,
    batch_context=None,
) -> DocumentsApplicationService:
    """Wire all dependencies for the documents bounded context.

    ``batch_context`` (optional) is a contextmanager factory that yields a
    fresh ``(DocumentRepository, UnitOfWork)`` pair on every embedding-batch
    flush. Pass it from bulk-ingest scripts so concurrent batches don't fight
    over a single DB session. API request handlers leave it as ``None``.
    """
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
        batch_context=batch_context,
    )

    return DocumentsApplicationService(
        ingest_use_case=ingest_use_case,
        document_repository=repository,
    )
