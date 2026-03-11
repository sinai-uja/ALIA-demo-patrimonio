"""Unit tests for Documents API Pydantic schemas."""

import pytest
from pydantic import ValidationError

from src.api.v1.endpoints.documents.schemas import (
    ChunkResponse,
    IngestRequest,
    IngestResponse,
)


class TestIngestRequest:
    def test_valid_request(self):
        req = IngestRequest(
            source_path="/data/iaph/patrimonio_inmueble",
            heritage_type="patrimonio_inmueble",
        )
        assert req.source_path == "/data/iaph/patrimonio_inmueble"
        assert req.heritage_type == "patrimonio_inmueble"
        assert req.chunk_size == 512
        assert req.chunk_overlap == 64

    def test_custom_chunk_params(self):
        req = IngestRequest(
            source_path="/data",
            heritage_type="BIC",
            chunk_size=256,
            chunk_overlap=32,
        )
        assert req.chunk_size == 256
        assert req.chunk_overlap == 32

    def test_missing_source_path_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            IngestRequest(heritage_type="patrimonio_inmueble")  # type: ignore[call-arg]
        errors = exc_info.value.errors()
        field_names = [e["loc"][0] for e in errors]
        assert "source_path" in field_names

    def test_missing_heritage_type_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            IngestRequest(source_path="/data")  # type: ignore[call-arg]
        errors = exc_info.value.errors()
        field_names = [e["loc"][0] for e in errors]
        assert "heritage_type" in field_names


class TestIngestResponse:
    def test_valid_response(self):
        resp = IngestResponse(
            total_documents=10,
            total_chunks=150,
            skipped_chunks=3,
            message="Ingestion complete",
        )
        assert resp.total_documents == 10
        assert resp.total_chunks == 150
        assert resp.skipped_chunks == 3
        assert resp.message == "Ingestion complete"


class TestChunkResponse:
    def test_valid_chunk_response(self):
        resp = ChunkResponse(
            id="abc-123",
            document_id="doc-1",
            content="Texto del fragmento.",
            chunk_index=0,
            token_count=5,
        )
        assert resp.id == "abc-123"
        assert resp.chunk_index == 0
