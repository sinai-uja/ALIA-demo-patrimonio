"""Tests for IngestDocumentsUseCase — documents context."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.application.documents.dto.ingest_dto import IngestDocumentsCommand, IngestResultDTO
from src.application.documents.use_cases.ingest_documents import IngestDocumentsUseCase
from src.domain.documents.entities.chunk import Chunk
from src.domain.documents.services.document_enrichment_service import DocumentEnrichmentService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_document():
    doc = MagicMock()
    doc.id = "doc-1"
    doc.heritage_type = "inmueble"
    doc.metadata = {}
    return doc


def _make_chunk(doc_id="doc-1", chunk_index=0):
    return Chunk(
        id=uuid.uuid4(),
        document_id=doc_id,
        content="chunk content",
        chunk_index=chunk_index,
        token_count=10,
    )


def _make_enriched_content():
    ec = MagicMock()
    ec.text = "enriched chunk content"
    return ec


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def document_loader():
    loader = MagicMock()
    doc = _make_document()
    loader.load_documents.return_value = [doc]
    return loader, doc


@pytest.fixture
def chunking_service():
    svc = MagicMock()
    svc.chunk_document.return_value = [_make_chunk(chunk_index=0), _make_chunk(chunk_index=1)]
    return svc


@pytest.fixture
def embedding_port():
    port = AsyncMock()
    port.embed.return_value = [[0.1, 0.2], [0.3, 0.4]]
    return port


@pytest.fixture
def document_repository():
    repo = AsyncMock()
    repo.chunk_exists.return_value = False
    repo.save_chunk_with_embedding.return_value = None
    return repo


@pytest.fixture
def enrichment_service():
    svc = MagicMock(spec=DocumentEnrichmentService)
    svc.enrich.return_value = _make_enriched_content()
    return svc


@pytest.fixture
def use_case(document_loader, chunking_service, embedding_port, document_repository, enrichment_service, mock_uow):
    loader, _ = document_loader
    return IngestDocumentsUseCase(
        document_loader=loader,
        chunking_service=chunking_service,
        embedding_port=embedding_port,
        document_repository=document_repository,
        enrichment_service=enrichment_service,
        unit_of_work=mock_uow,
    )


def _cmd(**overrides):
    defaults = dict(source_path="/data/inmuebles.parquet", heritage_type="patrimonio_inmueble")
    defaults.update(overrides)
    return IngestDocumentsCommand(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_happy_path_returns_ingest_result(use_case):
    result = await use_case.execute(_cmd())
    assert isinstance(result, IngestResultDTO)
    assert result.total_documents == 1
    assert result.total_chunks == 2
    assert result.skipped_chunks == 0


@pytest.mark.asyncio
async def test_existing_chunks_skipped(use_case, document_repository):
    # First chunk exists, second does not
    document_repository.chunk_exists.side_effect = [True, False]
    result = await use_case.execute(_cmd())
    assert result.total_chunks == 1
    assert result.skipped_chunks == 1


@pytest.mark.asyncio
async def test_all_chunks_skipped(use_case, document_repository):
    document_repository.chunk_exists.return_value = True
    result = await use_case.execute(_cmd())
    assert result.total_chunks == 0
    assert result.skipped_chunks == 2


@pytest.mark.asyncio
async def test_uow_wraps_persistence(use_case, mock_uow):
    await use_case.execute(_cmd())
    mock_uow.__aenter__.assert_awaited()
    mock_uow.__aexit__.assert_awaited()


@pytest.mark.asyncio
async def test_embed_called_with_enriched_texts(use_case, embedding_port, enrichment_service):
    await use_case.execute(_cmd())
    embedding_port.embed.assert_awaited()
    # The embed call should use the enriched text
    call_args = embedding_port.embed.call_args[0][0]
    assert all("enriched" in t for t in call_args)


@pytest.mark.asyncio
async def test_enrichment_called_per_chunk(use_case, enrichment_service):
    await use_case.execute(_cmd())
    assert enrichment_service.enrich.call_count == 2


@pytest.mark.asyncio
async def test_save_chunk_called_per_new_chunk(use_case, document_repository):
    await use_case.execute(_cmd())
    assert document_repository.save_chunk_with_embedding.await_count == 2


@pytest.mark.asyncio
async def test_chunk_size_from_command_applied(use_case, chunking_service):
    await use_case.execute(_cmd(chunk_size=1024, chunk_overlap=128))
    assert chunking_service.chunk_size == 1024
    assert chunking_service.chunk_overlap == 128
