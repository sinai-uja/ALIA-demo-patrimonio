"""Unit tests for ChunkingService."""

import pytest

from src.domain.documents.entities.document import Document
from src.domain.documents.exceptions import InvalidChunkingConfigurationError
from src.domain.documents.services.chunking_service import ChunkingService
from src.domain.documents.value_objects.heritage_type import HeritageType


def _make_document(text: str, doc_id: str = "doc-1") -> Document:
    """Helper to build a Document with minimal required fields."""
    return Document(
        id=doc_id,
        url="https://example.com/doc",
        title="Test Document",
        province="Jaen",
        heritage_type=HeritageType.PATRIMONIO_INMUEBLE,
        text=text,
    )


class TestChunkingServiceInit:
    def test_default_parameters(self):
        service = ChunkingService()
        assert service.chunk_size == 512
        assert service.chunk_overlap == 64

    def test_custom_parameters(self):
        service = ChunkingService(chunk_size=100, chunk_overlap=10)
        assert service.chunk_size == 100
        assert service.chunk_overlap == 10

    def test_overlap_greater_or_equal_to_size_raises(self):
        with pytest.raises(
            InvalidChunkingConfigurationError,
            match="chunk_overlap must be less than chunk_size",
        ):
            ChunkingService(chunk_size=100, chunk_overlap=100)

    def test_overlap_exceeds_size_raises(self):
        with pytest.raises(
            InvalidChunkingConfigurationError,
            match="chunk_overlap must be less than chunk_size",
        ):
            ChunkingService(chunk_size=50, chunk_overlap=60)


class TestChunkDocument:
    def test_empty_text_returns_empty_list(self):
        service = ChunkingService(chunk_size=10, chunk_overlap=2)
        doc = _make_document("")
        chunks = service.chunk_document(doc)
        assert chunks == []

    def test_whitespace_only_text_returns_empty_list(self):
        service = ChunkingService(chunk_size=10, chunk_overlap=2)
        doc = _make_document("   \n\t  ")
        chunks = service.chunk_document(doc)
        assert chunks == []

    def test_short_text_produces_one_chunk(self):
        service = ChunkingService(chunk_size=10, chunk_overlap=2)
        doc = _make_document("uno dos tres")
        chunks = service.chunk_document(doc)

        assert len(chunks) == 1
        assert chunks[0].content == "uno dos tres"
        assert chunks[0].chunk_index == 0
        assert chunks[0].token_count == 3
        assert chunks[0].document_id == "doc-1"

    def test_long_text_produces_multiple_chunks(self):
        words = " ".join(f"w{i}" for i in range(25))
        service = ChunkingService(chunk_size=10, chunk_overlap=2)
        doc = _make_document(words)
        chunks = service.chunk_document(doc)

        assert len(chunks) > 1
        # First chunk has exactly chunk_size words
        assert chunks[0].token_count == 10

    def test_chunk_indices_are_sequential(self):
        words = " ".join(f"w{i}" for i in range(50))
        service = ChunkingService(chunk_size=10, chunk_overlap=2)
        doc = _make_document(words)
        chunks = service.chunk_document(doc)

        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_chunks_overlap_correctly(self):
        # 20 words, chunk_size=10, overlap=3, step=7
        words = [f"w{i}" for i in range(20)]
        text = " ".join(words)
        service = ChunkingService(chunk_size=10, chunk_overlap=3)
        doc = _make_document(text)
        chunks = service.chunk_document(doc)

        # First chunk: words 0-9, second chunk: words 7-16
        first_words = chunks[0].content.split()
        second_words = chunks[1].content.split()
        # The overlap region is the last 3 words of chunk 0 matching first 3 of chunk 1
        assert first_words[7:10] == second_words[0:3]

    def test_all_chunks_have_correct_document_id(self):
        words = " ".join(f"w{i}" for i in range(30))
        service = ChunkingService(chunk_size=10, chunk_overlap=2)
        doc = _make_document(words, doc_id="heritage-42")
        chunks = service.chunk_document(doc)

        for chunk in chunks:
            assert chunk.document_id == "heritage-42"

    def test_all_chunks_have_unique_ids(self):
        words = " ".join(f"w{i}" for i in range(30))
        service = ChunkingService(chunk_size=10, chunk_overlap=2)
        doc = _make_document(words)
        chunks = service.chunk_document(doc)

        ids = [c.id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_tiny_trailing_chunk_is_avoided(self):
        # With chunk_size=10, overlap=3, step=7: starts at 0,7,14
        # 17 words: after chunk at start=14, remaining=3 words which equals overlap -> break
        # So we expect 2 chunks (0-9, 7-16) instead of a tiny third chunk
        words = " ".join(f"w{i}" for i in range(17))
        service = ChunkingService(chunk_size=10, chunk_overlap=3)
        doc = _make_document(words)
        chunks = service.chunk_document(doc)

        # The last chunk should not be tiny (<=overlap words)
        assert chunks[-1].token_count > 3

    def test_exact_chunk_size_text(self):
        words = " ".join(f"w{i}" for i in range(10))
        service = ChunkingService(chunk_size=10, chunk_overlap=2)
        doc = _make_document(words)
        chunks = service.chunk_document(doc)

        assert len(chunks) == 1
        assert chunks[0].token_count == 10
