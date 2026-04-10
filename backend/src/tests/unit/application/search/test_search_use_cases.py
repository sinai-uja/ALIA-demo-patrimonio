"""Tests for search use cases (similarity, suggestion, filter_values)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.application.search.dto.search_dto import (
    FilterValuesDTO,
    SimilaritySearchDTO,
    SimilaritySearchResponseDTO,
    SuggestionResponseDTO,
)
from src.application.search.use_cases.filter_values_use_case import FilterValuesUseCase
from src.application.search.use_cases.similarity_search_use_case import SimilaritySearchUseCase
from src.application.search.use_cases.suggestion_use_case import SuggestionUseCase
from src.domain.rag.entities.retrieved_chunk import RetrievedChunk


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chunk(doc_id="doc-1", score=0.1, title="Castle"):
    return RetrievedChunk(
        chunk_id="c1",
        document_id=doc_id,
        title=title,
        heritage_type="inmueble",
        province="Jaen",
        municipality="Jaen",
        url="http://example.com",
        content="content",
        score=score,
    )


# ---------------------------------------------------------------------------
# SimilaritySearchUseCase
# ---------------------------------------------------------------------------


@pytest.fixture
def similarity_uc():
    embedding_port = AsyncMock()
    embedding_port.embed.return_value = [[0.1, 0.2]]
    vector_port = AsyncMock()
    vector_port.search.return_value = [_make_chunk()]
    text_port = AsyncMock()
    text_port.search.return_value = [_make_chunk(score=0.2)]
    hybrid_svc = MagicMock()
    hybrid_svc.fuse.return_value = [_make_chunk()]
    relevance_svc = MagicMock()
    relevance_svc.filter.side_effect = lambda c: c
    reranking_svc = MagicMock()
    reranking_svc.rerank.return_value = [_make_chunk()]
    heritage_lookup = AsyncMock()
    heritage_lookup.get_summaries_by_ids.return_value = {}

    uc = SimilaritySearchUseCase(
        embedding_port=embedding_port,
        vector_search_port=vector_port,
        text_search_port=text_port,
        hybrid_search_service=hybrid_svc,
        relevance_filter_service=relevance_svc,
        reranking_service=reranking_svc,
        heritage_asset_lookup_port=heritage_lookup,
        similarity_only=False,
        reranker_enabled=False,
    )
    return uc, embedding_port, vector_port, text_port


@pytest.mark.asyncio
async def test_similarity_search_returns_response_dto(similarity_uc):
    uc, _, _, _ = similarity_uc
    result = await uc.execute(SimilaritySearchDTO(query="castillos"))
    assert isinstance(result, SimilaritySearchResponseDTO)
    assert result.total_results >= 1


@pytest.mark.asyncio
async def test_similarity_search_embeds_query(similarity_uc):
    uc, embedding_port, _, _ = similarity_uc
    await uc.execute(SimilaritySearchDTO(query="test query"))
    embedding_port.embed.assert_awaited_once()


# ---------------------------------------------------------------------------
# SuggestionUseCase
# ---------------------------------------------------------------------------


@pytest.fixture
def suggestion_uc():
    filter_port = AsyncMock()
    filter_port.get_distinct_provinces.return_value = ["Jaen", "Cordoba"]
    filter_port.get_distinct_municipalities.return_value = ["Jaen", "Ubeda"]
    filter_port.get_distinct_heritage_types.return_value = ["inmueble", "mueble"]
    entity_svc = MagicMock()
    entity_svc.detect.return_value = []
    return SuggestionUseCase(
        filter_metadata_port=filter_port,
        entity_detection_service=entity_svc,
    ), entity_svc, filter_port


@pytest.mark.asyncio
async def test_suggestion_returns_response_dto(suggestion_uc):
    uc, _, _ = suggestion_uc
    result = await uc.execute("castillos en Jaen")
    assert isinstance(result, SuggestionResponseDTO)
    assert result.query == "castillos en Jaen"


@pytest.mark.asyncio
async def test_suggestion_calls_entity_detection(suggestion_uc):
    uc, entity_svc, _ = suggestion_uc
    await uc.execute("castillos en Jaen")
    entity_svc.detect.assert_called_once()


# ---------------------------------------------------------------------------
# FilterValuesUseCase
# ---------------------------------------------------------------------------


@pytest.fixture
def filter_values_uc():
    filter_port = AsyncMock()
    filter_port.get_distinct_heritage_types.return_value = ["inmueble"]
    filter_port.get_distinct_provinces.return_value = ["Jaen"]
    filter_port.get_distinct_municipalities.return_value = ["Ubeda"]
    return FilterValuesUseCase(filter_metadata_port=filter_port), filter_port


@pytest.mark.asyncio
async def test_filter_values_returns_dto(filter_values_uc):
    uc, _ = filter_values_uc
    result = await uc.execute()
    assert isinstance(result, FilterValuesDTO)
    assert result.heritage_types == ["inmueble"]
    assert result.provinces == ["Jaen"]
    assert result.municipalities == ["Ubeda"]


@pytest.mark.asyncio
async def test_filter_values_passes_province_filter(filter_values_uc):
    uc, port = filter_values_uc
    await uc.execute(provinces=["Jaen"])
    call_kwargs = port.get_distinct_municipalities.call_args.kwargs
    assert call_kwargs["provinces"] == ["Jaen"]
