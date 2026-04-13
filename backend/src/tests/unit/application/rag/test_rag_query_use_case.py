"""Tests for RAGQueryUseCase — rag context."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.rag.dto.rag_dto import RAGQueryDTO, RAGResponseDTO
from src.application.rag.use_cases.rag_query_use_case import (
    ABSTENTION_ANSWER,
    RAGQueryUseCase,
)
from src.domain.rag.entities.retrieved_chunk import RetrievedChunk

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chunk(score=0.1, title="Chunk", doc_id="doc-1"):
    return RetrievedChunk(
        chunk_id="c1",
        document_id=doc_id,
        title=title,
        heritage_type="inmueble",
        province="Jaen",
        municipality="Jaen",
        url="http://example.com",
        content="chunk content",
        score=score,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def embedding_port():
    port = AsyncMock()
    port.embed.return_value = [[0.1, 0.2, 0.3]]
    return port


@pytest.fixture
def vector_search_port():
    port = AsyncMock()
    port.search.return_value = [_make_chunk()]
    return port


@pytest.fixture
def text_search_port():
    port = AsyncMock()
    port.search.return_value = [_make_chunk(score=0.2)]
    return port


@pytest.fixture
def llm_port():
    port = AsyncMock()
    port.generate.return_value = "LLM generated answer"
    return port


@pytest.fixture
def context_assembly_service():
    svc = MagicMock()
    svc.assemble.return_value = "assembled context"
    return svc


@pytest.fixture
def relevance_filter_service():
    svc = MagicMock()
    svc.filter.side_effect = lambda chunks: chunks  # pass-through
    return svc


@pytest.fixture
def hybrid_search_service():
    svc = MagicMock()
    svc.fuse.return_value = [_make_chunk()]
    return svc


@pytest.fixture
def reranking_service():
    svc = MagicMock()
    svc.rerank.return_value = [_make_chunk()]
    return svc


@pytest.fixture
def use_case(
    embedding_port,
    vector_search_port,
    text_search_port,
    llm_port,
    context_assembly_service,
    relevance_filter_service,
    hybrid_search_service,
    reranking_service,
):
    """Default: hybrid mode (similarity_only=False), reranker disabled."""
    return RAGQueryUseCase(
        embedding_port=embedding_port,
        vector_search_port=vector_search_port,
        text_search_port=text_search_port,
        llm_port=llm_port,
        context_assembly_service=context_assembly_service,
        relevance_filter_service=relevance_filter_service,
        hybrid_search_service=hybrid_search_service,
        reranking_service=reranking_service,
        retrieval_k=20,
        similarity_only=False,
        reranker_enabled=False,
    )


def _dto(**overrides):
    defaults = dict(query="castillos en Jaen", top_k=5)
    defaults.update(overrides)
    return RAGQueryDTO(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_pipeline_happy_path(
    use_case, embedding_port, vector_search_port, text_search_port, llm_port,
):
    result = await use_case.execute(_dto())
    assert isinstance(result, RAGResponseDTO)
    assert result.answer == "LLM generated answer"
    assert not result.abstained
    embedding_port.embed.assert_awaited_once()
    vector_search_port.search.assert_awaited_once()
    text_search_port.search.assert_awaited_once()
    llm_port.generate.assert_awaited_once()


@pytest.mark.asyncio
async def test_similarity_only_skips_text_search(
    embedding_port,
    vector_search_port,
    text_search_port,
    llm_port,
    context_assembly_service,
    relevance_filter_service,
    hybrid_search_service,
    reranking_service,
):
    uc = RAGQueryUseCase(
        embedding_port=embedding_port,
        vector_search_port=vector_search_port,
        text_search_port=text_search_port,
        llm_port=llm_port,
        context_assembly_service=context_assembly_service,
        relevance_filter_service=relevance_filter_service,
        hybrid_search_service=hybrid_search_service,
        reranking_service=reranking_service,
        similarity_only=True,
    )
    result = await uc.execute(_dto())
    assert isinstance(result, RAGResponseDTO)
    text_search_port.search.assert_not_awaited()
    hybrid_search_service.fuse.assert_not_called()


@pytest.mark.asyncio
async def test_no_relevant_chunks_returns_abstention(
    use_case, relevance_filter_service,
):
    relevance_filter_service.filter.side_effect = None
    relevance_filter_service.filter.return_value = []
    result = await use_case.execute(_dto())
    assert result.abstained is True
    assert result.answer == ABSTENTION_ANSWER
    assert result.sources == []


@pytest.mark.asyncio
async def test_filters_propagated_to_vector_search(use_case, vector_search_port):
    await use_case.execute(
        _dto(heritage_type_filter="inmueble", province_filter="Jaen")
    )
    call_kwargs = vector_search_port.search.call_args.kwargs
    assert call_kwargs["heritage_type"] == "inmueble"
    assert call_kwargs["province"] == "Jaen"


@pytest.mark.asyncio
async def test_filters_propagated_to_text_search(use_case, text_search_port):
    await use_case.execute(
        _dto(heritage_type_filter="inmueble", province_filter="Jaen")
    )
    call_kwargs = text_search_port.search.call_args.kwargs
    assert call_kwargs["heritage_type"] == "inmueble"
    assert call_kwargs["province"] == "Jaen"


@pytest.mark.asyncio
async def test_reranker_discards_all_returns_abstention(use_case, reranking_service):
    reranking_service.rerank.return_value = []
    result = await use_case.execute(_dto())
    assert result.abstained is True


@pytest.mark.asyncio
async def test_sources_in_response_match_final_chunks(use_case):
    result = await use_case.execute(_dto())
    assert len(result.sources) >= 1
    assert result.sources[0].title == "Chunk"


@pytest.mark.asyncio
async def test_query_lowercased_for_embedding(use_case, embedding_port):
    await use_case.execute(_dto(query="CASTILLOS EN JAEN"))
    call_args = embedding_port.embed.call_args[0][0]
    # The text passed to embed should contain the lowercased query
    assert "castillos en jaen" in call_args[0].lower()
