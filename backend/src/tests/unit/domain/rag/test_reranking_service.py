"""Unit tests for RerankingService — pure domain, zero mocks."""

import pytest

from src.domain.rag.entities.retrieved_chunk import RetrievedChunk
from src.domain.rag.services.reranking_service import RerankingService


def _make_chunk(
    chunk_id: str = "c1",
    title: str = "Castillo de Jaén",
    content: str = "El castillo fue construido en el siglo XIII.",
    score: float = 0.3,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id=f"doc-{chunk_id}",
        title=title,
        heritage_type="patrimonio_inmueble",
        province="Jaén",
        municipality="Jaén",
        url=f"https://example.com/{chunk_id}",
        content=content,
        score=score,
    )


class TestPreFilter:
    def test_discards_chunks_without_lexical_match(self):
        service = RerankingService()
        chunks = [
            _make_chunk("c1", title="Catedral de Sevilla", content="Templo gótico impresionante"),
        ]

        result = service.rerank("castillo de Jaén", chunks, top_k=10)

        # "castillo" and "jaen" appear nowhere in title/content of this chunk
        assert len(result) == 0

    def test_keeps_chunks_with_title_match(self):
        service = RerankingService()
        chunks = [_make_chunk("c1", title="Castillo de Santa Catalina")]

        result = service.rerank("castillo", chunks, top_k=10)

        assert len(result) == 1

    def test_keeps_chunks_with_content_match(self):
        service = RerankingService()
        chunks = [_make_chunk("c1", title="Fortaleza", content="Este castillo domina la ciudad")]

        result = service.rerank("castillo", chunks, top_k=10)

        assert len(result) == 1

    def test_all_discarded_returns_empty(self):
        service = RerankingService()
        chunks = [
            _make_chunk("c1", title="abc", content="def"),
            _make_chunk("c2", title="ghi", content="jkl"),
        ]

        result = service.rerank("zzz", chunks, top_k=10)

        assert result == []


class TestScoringAndWeights:
    def test_title_match_boosts_ranking(self):
        service = RerankingService(weight_title=0.9, weight_base=0.1, weight_coverage=0.0, weight_position=0.0)
        high_title = _make_chunk("c1", title="Castillo de Jaén", content="info general")
        low_title = _make_chunk("c2", title="Documento sobre la zona", content="castillo ruinas")

        result = service.rerank("castillo", [low_title, high_title], top_k=10)

        assert result[0].chunk_id == "c1"

    def test_configurable_weights_change_ranking(self):
        # With coverage weight dominant, the chunk with more query terms in content wins
        service = RerankingService(weight_base=0.0, weight_title=0.0, weight_coverage=1.0, weight_position=0.0)
        low_coverage = _make_chunk("c1", title="castillo", content="breve")
        high_coverage = _make_chunk("c2", title="castillo", content="castillo medieval en jaen")

        result = service.rerank("castillo medieval jaen", [low_coverage, high_coverage], top_k=10)

        assert result[0].chunk_id == "c2"


class TestTopKAndEdgeCases:
    def test_top_k_limits_results(self):
        service = RerankingService()
        chunks = [_make_chunk(f"c{i}", title="castillo", content="castillo") for i in range(10)]

        result = service.rerank("castillo", chunks, top_k=3)

        assert len(result) == 3

    def test_empty_input_returns_empty(self):
        service = RerankingService()

        result = service.rerank("castillo", [], top_k=10)

        assert result == []


class TestStopwordFiltering:
    def test_stopwords_are_filtered_from_query(self):
        service = RerankingService()
        # "dame informacion de la" are all stopwords — only "catedral" remains
        chunks = [_make_chunk("c1", title="Catedral de Sevilla", content="templo")]

        result = service.rerank("dame informacion de la catedral", chunks, top_k=10)

        assert len(result) == 1

    def test_query_with_only_stopwords_returns_chunks_unchanged(self):
        service = RerankingService()
        chunks = [_make_chunk("c1")]

        result = service.rerank("de la el los", chunks, top_k=10)

        # All tokens are stopwords → query_terms empty → return chunks[:top_k] unmodified
        assert len(result) == 1
