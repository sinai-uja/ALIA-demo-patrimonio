"""Tests for search use cases (similarity, suggestion, filter_values)."""

from unittest.mock import AsyncMock, MagicMock

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
    relevance_svc.filter.side_effect = lambda c, **_kw: c
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


@pytest.mark.asyncio
async def test_similarity_search_propagates_score_threshold_to_filter_hybrid():
    """Hybrid branch: per-request score_threshold must reach the relevance filter."""
    embedding_port = AsyncMock()
    embedding_port.embed.return_value = [[0.1, 0.2]]
    vector_port = AsyncMock()
    vector_port.search.return_value = [_make_chunk()]
    text_port = AsyncMock()
    text_port.search.return_value = [_make_chunk(score=0.2)]
    hybrid_svc = MagicMock()
    hybrid_svc.fuse.return_value = [_make_chunk()]
    relevance_svc = MagicMock()
    relevance_svc.filter.return_value = [_make_chunk()]
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

    await uc.execute(SimilaritySearchDTO(query="castillos", score_threshold=0.33))

    # Filter must have been called with the per-request override.
    relevance_svc.filter.assert_called_once()
    call_kwargs = relevance_svc.filter.call_args.kwargs
    assert call_kwargs.get("override_threshold") == 0.33


@pytest.mark.asyncio
async def test_similarity_search_propagates_score_threshold_to_filter_similarity_only():
    """Similarity-only branch: per-request score_threshold must reach the
    similarity filter."""
    embedding_port = AsyncMock()
    embedding_port.embed.return_value = [[0.1, 0.2]]
    vector_port = AsyncMock()
    vector_port.search.return_value = [_make_chunk()]
    text_port = AsyncMock()
    hybrid_svc = MagicMock()
    relevance_svc = MagicMock()
    reranking_svc = MagicMock()
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
        similarity_only=True,
        similarity_threshold=0.50,
        reranker_enabled=False,
    )

    await uc.execute(SimilaritySearchDTO(query="castillos", score_threshold=0.25))

    # In similarity-only the use case builds its own internal filter; we can
    # assert behavior through the resulting chunks. With score=0.1 (from
    # _make_chunk) the chunk should survive an override of 0.25.
    # If no override was honored, the constructed filter would still keep it
    # too (since the constructor default is 0.50). To make the test
    # meaningful we re-run with a stricter override and assert the result.
    vector_port.search.return_value = [_make_chunk(score=0.40)]
    result = await uc.execute(
        SimilaritySearchDTO(query="castillos", score_threshold=0.30),
    )
    # The 0.40 chunk should be filtered out by the 0.30 override.
    assert result.total_results == 0


@pytest.mark.asyncio
async def test_similarity_search_default_threshold_when_not_provided(similarity_uc):
    """When DTO score_threshold is None, override must be passed as None
    (so the constructor default applies)."""
    uc, _, _, _ = similarity_uc
    # Replace the mocked filter to track invocation.
    relevance_svc = MagicMock()
    relevance_svc.filter.return_value = [_make_chunk()]
    uc._relevance_filter_service = relevance_svc

    await uc.execute(SimilaritySearchDTO(query="castillos"))

    call_kwargs = relevance_svc.filter.call_args.kwargs
    assert call_kwargs.get("override_threshold") is None


# ---------------------------------------------------------------------------
# Lexical weight slider behaviour
# ---------------------------------------------------------------------------


def _build_uc(
    *,
    similarity_only: bool = False,
    reranker_enabled: bool = False,
    default_lexical_weight: float = 0.5,
):
    """Build a SimilaritySearchUseCase + its mocked collaborators."""
    embedding_port = AsyncMock()
    embedding_port.embed.return_value = [[0.1, 0.2]]
    vector_port = AsyncMock()
    vector_port.search.return_value = [_make_chunk(doc_id="vdoc")]
    text_port = AsyncMock()
    text_port.search.return_value = [_make_chunk(doc_id="tdoc", score=0.3)]
    hybrid_svc = MagicMock()
    hybrid_svc.fuse.return_value = [_make_chunk(doc_id="vdoc")]
    relevance_svc = MagicMock()
    relevance_svc.filter.side_effect = lambda c, **_kw: c
    reranking_svc = AsyncMock()
    reranking_svc.rerank.return_value = [_make_chunk(doc_id="vdoc")]
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
        similarity_only=similarity_only,
        similarity_threshold=0.99,  # don't filter anything out in tests
        reranker_enabled=reranker_enabled,
        default_lexical_weight=default_lexical_weight,
    )
    return uc, embedding_port, vector_port, text_port, hybrid_svc, reranking_svc


@pytest.mark.asyncio
async def test_similarity_only_settings_with_no_request_weight_matches_legacy_flow():
    """RAG_SIMILARITY_ONLY=true + DTO without lexical_weight must take the
    semantic-only branch (no text search, no fusion)."""
    uc, embedding_port, vector_port, text_port, hybrid_svc, _ = _build_uc(
        similarity_only=True,
    )

    await uc.execute(SimilaritySearchDTO(query="castillos"))

    embedding_port.embed.assert_awaited_once()
    vector_port.search.assert_awaited_once()
    text_port.search.assert_not_called()
    hybrid_svc.fuse.assert_not_called()


@pytest.mark.asyncio
async def test_lexical_weight_one_skips_embedding_and_vector_search():
    """`lexical_weight=1.0` → lexical-only branch: no embedding, no vector."""
    uc, embedding_port, vector_port, text_port, hybrid_svc, _ = _build_uc()

    await uc.execute(SimilaritySearchDTO(query="zurbarán", lexical_weight=1.0))

    embedding_port.embed.assert_not_called()
    vector_port.search.assert_not_called()
    text_port.search.assert_awaited_once()
    hybrid_svc.fuse.assert_not_called()


@pytest.mark.asyncio
async def test_lexical_weight_zero_skips_text_search():
    """`lexical_weight=0.0` → semantic-only branch: no text search."""
    uc, embedding_port, vector_port, text_port, hybrid_svc, _ = _build_uc()

    await uc.execute(SimilaritySearchDTO(query="castillo", lexical_weight=0.0))

    embedding_port.embed.assert_awaited_once()
    vector_port.search.assert_awaited_once()
    text_port.search.assert_not_called()
    hybrid_svc.fuse.assert_not_called()


@pytest.mark.asyncio
async def test_intermediate_weight_runs_full_hybrid_pipeline():
    """`lexical_weight in (0,1)` → all of embed, vector, text and fuse called.

    The fusion must receive the per-request `lexical_weight` value.
    """
    uc, embedding_port, vector_port, text_port, hybrid_svc, _ = _build_uc()

    await uc.execute(SimilaritySearchDTO(query="castillo", lexical_weight=0.7))

    embedding_port.embed.assert_awaited_once()
    vector_port.search.assert_awaited_once()
    text_port.search.assert_awaited_once()
    hybrid_svc.fuse.assert_called_once()
    fuse_kwargs = hybrid_svc.fuse.call_args.kwargs
    assert fuse_kwargs.get("lexical_weight") == pytest.approx(0.7)


@pytest.mark.asyncio
async def test_request_weight_overrides_similarity_only_setting():
    """If RAG_SIMILARITY_ONLY=true but the request sends `lexical_weight`,
    the request wins (user intent overrides server default)."""
    uc, _, _, text_port, hybrid_svc, _ = _build_uc(similarity_only=True)

    await uc.execute(SimilaritySearchDTO(query="zurbarán", lexical_weight=1.0))

    # Lexical-only path engaged despite similarity_only=True at construction.
    text_port.search.assert_awaited_once()
    hybrid_svc.fuse.assert_not_called()


@pytest.mark.asyncio
async def test_default_lexical_weight_is_used_when_request_omits_field():
    """When the DTO omits `lexical_weight` and similarity_only=False, the use
    case must fall back to the server-configured default."""
    uc, _, _, _, hybrid_svc, _ = _build_uc(default_lexical_weight=0.3)

    await uc.execute(SimilaritySearchDTO(query="castillo"))

    hybrid_svc.fuse.assert_called_once()
    fuse_kwargs = hybrid_svc.fuse.call_args.kwargs
    assert fuse_kwargs.get("lexical_weight") == pytest.approx(0.3)


@pytest.mark.asyncio
async def test_reranker_in_hybrid_mode_runs_over_vector_chunks_only():
    """The reranker must receive the vector lane, NOT the fused output.

    This is the architectural fix that resolves the "Zurbarán" 1-token case.
    """
    uc, _, vector_port, _, hybrid_svc, reranking_svc = _build_uc(
        reranker_enabled=True,
    )
    # Distinct chunk sets so we can assert *which* list reached the reranker.
    vector_chunks = [_make_chunk(doc_id="vdoc-1"), _make_chunk(doc_id="vdoc-2")]
    vector_port.search.return_value = vector_chunks
    reranking_svc.rerank.return_value = vector_chunks

    await uc.execute(SimilaritySearchDTO(query="castillo", lexical_weight=0.5))

    reranking_svc.rerank.assert_awaited_once()
    rerank_kwargs = reranking_svc.rerank.call_args.kwargs
    # Must be the vector lane, not anything coming out of fuse.
    assert rerank_kwargs.get("chunks") == vector_chunks
    # And the rerank call must happen before fusion is invoked — the reranked
    # chunks are what we expect to be passed as vector_results to fuse.
    fuse_kwargs = hybrid_svc.fuse.call_args.kwargs
    assert fuse_kwargs.get("vector_results") == vector_chunks


@pytest.mark.asyncio
async def test_reranker_in_semantic_only_mode_runs_over_vector_chunks():
    """Semantic-only branch: the reranker still operates on vector chunks."""
    uc, _, vector_port, _, _, reranking_svc = _build_uc(
        reranker_enabled=True,
    )
    vector_chunks = [_make_chunk(doc_id="vdoc-1"), _make_chunk(doc_id="vdoc-2")]
    vector_port.search.return_value = vector_chunks
    reranking_svc.rerank.return_value = vector_chunks

    await uc.execute(SimilaritySearchDTO(query="castillo", lexical_weight=0.0))

    reranking_svc.rerank.assert_awaited_once()
    rerank_kwargs = reranking_svc.rerank.call_args.kwargs
    assert rerank_kwargs.get("chunks") == vector_chunks


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
