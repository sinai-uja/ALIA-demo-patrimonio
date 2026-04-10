"""Unit tests for DocumentEnrichmentService — pure domain, zero mocks."""

from uuid import uuid4

import pytest

from src.domain.documents.entities.chunk import Chunk
from src.domain.documents.entities.document import Document
from src.domain.documents.services.document_enrichment_service import (
    DocumentEnrichmentService,
    EnrichedContent,
)
from src.domain.documents.value_objects.heritage_type import HeritageType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_document(
    heritage_type: HeritageType = HeritageType.PATRIMONIO_INMUEBLE,
    title: str = "Alcázar de Sevilla",
    province: str = "Sevilla",
    municipality: str | None = "Sevilla",
    metadata: dict | None = None,
) -> Document:
    return Document(
        id="doc-1",
        url="https://example.com/doc",
        title=title,
        province=province,
        heritage_type=heritage_type,
        text="full text here",
        municipality=municipality,
        metadata=metadata or {},
    )


def _make_chunk(content: str = "chunk body text") -> Chunk:
    return Chunk(
        id=uuid4(),
        document_id="doc-1",
        content=content,
        chunk_index=0,
        token_count=10,
    )


# ---------------------------------------------------------------------------
# v4 templates — one per HeritageType
# ---------------------------------------------------------------------------

class TestEnrichV4Paisaje:
    def test_paisaje_template_contains_title_and_province(self):
        doc = _make_document(
            heritage_type=HeritageType.PAISAJE_CULTURAL,
            title="Vega de Granada", province="Granada",
        )
        chunk = _make_chunk("descripción del paisaje")
        service = DocumentEnrichmentService(chunks_version="v4")

        result = service.enrich(doc, chunk)

        assert isinstance(result, EnrichedContent)
        assert "Paisaje cultural titulado 'Vega de Granada'" in result.text
        assert "provincia de 'Granada'" in result.text
        assert "descripción del paisaje" in result.text


class TestEnrichV4Inmaterial:
    def test_inmaterial_template_with_activity_and_topic(self):
        doc = _make_document(
            heritage_type=HeritageType.PATRIMONIO_INMATERIAL,
            title="Flamenco",
            metadata={"activity_types": "Danza", "subject_topic": "Artes escénicas"},
        )
        chunk = _make_chunk("cuerpo del chunk")
        service = DocumentEnrichmentService(chunks_version="v4")

        result = service.enrich(doc, chunk)

        assert "Bien inmaterial titulado 'Flamenco'" in result.text
        assert "clasificado como Danza" in result.text
        assert "categoría Artes escénicas" in result.text

    def test_inmaterial_template_activity_only(self):
        doc = _make_document(
            heritage_type=HeritageType.PATRIMONIO_INMATERIAL,
            title="Fiesta",
            metadata={"activity_types": "Ritual"},
        )
        service = DocumentEnrichmentService(chunks_version="v4")
        result = service.enrich(doc, _make_chunk())

        assert "clasificado como Ritual" in result.text
        assert "categoría" not in result.text

    def test_inmaterial_template_topic_only(self):
        doc = _make_document(
            heritage_type=HeritageType.PATRIMONIO_INMATERIAL,
            title="Copla",
            metadata={"subject_topic": "Música"},
        )
        service = DocumentEnrichmentService(chunks_version="v4")
        result = service.enrich(doc, _make_chunk())

        assert "de categoría Música" in result.text
        assert "clasificado como" not in result.text


class TestEnrichV4Inmueble:
    def test_inmueble_with_characterisation_and_type(self):
        doc = _make_document(
            heritage_type=HeritageType.PATRIMONIO_INMUEBLE,
            title="Catedral",
            metadata={"characterisation": "Religiosa", "type": "Catedral"},
        )
        service = DocumentEnrichmentService(chunks_version="v4")
        result = service.enrich(doc, _make_chunk())

        assert "Bien inmueble titulado 'Catedral'" in result.text
        assert "naturaleza Religiosa" in result.text
        assert "tipo Catedral" in result.text

    def test_inmueble_with_style_and_period(self):
        doc = _make_document(
            heritage_type=HeritageType.PATRIMONIO_INMUEBLE,
            title="Iglesia",
            metadata={"styles": "Barroco", "historic_periods": "Edad Moderna"},
        )
        service = DocumentEnrichmentService(chunks_version="v4")
        result = service.enrich(doc, _make_chunk())

        assert "estilo Barroco" in result.text
        assert "período histórico Edad Moderna" in result.text

    def test_inmueble_without_municipality(self):
        doc = _make_document(
            heritage_type=HeritageType.PATRIMONIO_INMUEBLE,
            title="Torre",
            municipality=None,
        )
        service = DocumentEnrichmentService(chunks_version="v4")
        result = service.enrich(doc, _make_chunk())

        assert "provincia de Sevilla" in result.text
        assert "municipio" not in result.text


class TestEnrichV4Mueble:
    def test_mueble_with_type(self):
        doc = _make_document(
            heritage_type=HeritageType.PATRIMONIO_MUEBLE,
            title="Retablo Mayor",
            metadata={"type": "Retablo"},
        )
        service = DocumentEnrichmentService(chunks_version="v4")
        result = service.enrich(doc, _make_chunk())

        assert "Bien mueble titulado 'Retablo Mayor' de tipo Retablo" in result.text

    def test_mueble_without_type(self):
        doc = _make_document(
            heritage_type=HeritageType.PATRIMONIO_MUEBLE,
            title="Escultura",
        )
        service = DocumentEnrichmentService(chunks_version="v4")
        result = service.enrich(doc, _make_chunk())

        assert "Bien mueble titulado 'Escultura'." in result.text
        assert "de tipo" not in result.text


# ---------------------------------------------------------------------------
# Legacy (non-v4) — pipe-separated header
# ---------------------------------------------------------------------------

class TestEnrichLegacyHeader:
    def test_legacy_header_contains_pipe_separated_fields(self):
        doc = _make_document(municipality="Córdoba", province="Córdoba")
        service = DocumentEnrichmentService(chunks_version="v2")
        result = service.enrich(doc, _make_chunk("legacy body"))

        assert " | " in result.text
        assert "Titulo: Alcázar de Sevilla" in result.text
        assert "Tipo: patrimonio_inmueble" in result.text
        assert "Municipio: Córdoba" in result.text
        assert "---" in result.text
        assert "legacy body" in result.text

    def test_legacy_header_omits_municipality_when_none(self):
        doc = _make_document(municipality=None)
        service = DocumentEnrichmentService(chunks_version="v1")
        result = service.enrich(doc, _make_chunk())

        assert "Municipio" not in result.text


# ---------------------------------------------------------------------------
# _get_meta — NaN, None, empty handling
# ---------------------------------------------------------------------------

class TestGetMeta:
    @pytest.mark.parametrize("value,expected", [
        (None, None),
        ("", None),
        ("  ", None),
        ("nan", None),
        ("NaN", None),
        ("NAN", None),
        (float("nan"), None),
        ("valid text", "valid text"),
        ("  padded  ", "padded"),
    ])
    def test_get_meta_handles_edge_values(self, value, expected):
        metadata = {"key": value} if value is not None else {}
        doc = _make_document(metadata=metadata)
        result = DocumentEnrichmentService._get_meta(doc, "key")

        if expected is None:
            assert result is None
        else:
            assert result == expected

    def test_get_meta_missing_key_returns_none(self):
        doc = _make_document(metadata={"other": "value"})
        assert DocumentEnrichmentService._get_meta(doc, "missing") is None


# ---------------------------------------------------------------------------
# Return type & immutability
# ---------------------------------------------------------------------------

class TestEnrichedContentReturnType:
    def test_enrich_returns_enriched_content_not_mutation(self):
        doc = _make_document()
        chunk = _make_chunk("original content")
        service = DocumentEnrichmentService(chunks_version="v4")

        result = service.enrich(doc, chunk)

        assert isinstance(result, EnrichedContent)
        assert chunk.content == "original content"  # chunk not mutated
        assert result.text != chunk.content  # enriched text differs
