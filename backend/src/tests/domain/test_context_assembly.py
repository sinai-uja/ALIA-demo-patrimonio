"""Unit tests for ContextAssemblyService."""

from src.domain.rag.entities.retrieved_chunk import RetrievedChunk
from src.domain.rag.services.context_assembly_service import ContextAssemblyService


def _make_chunk(
    title: str = "Catedral de Jaen",
    heritage_type: str = "patrimonio_inmueble",
    province: str = "Jaen",
    content: str = "La catedral renacentista...",
    url: str = "https://guiadigital.iaph.es/catedral-jaen",
    score: float = 0.95,
    chunk_id: str = "chunk-1",
    document_id: str = "doc-1",
    municipality: str | None = None,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        title=title,
        heritage_type=heritage_type,
        province=province,
        municipality=municipality,
        url=url,
        content=content,
        score=score,
    )


class TestContextAssemblyService:
    def test_empty_list_returns_empty_string(self):
        service = ContextAssemblyService()
        result = service.assemble([])
        assert result == ""

    def test_single_chunk_produces_formatted_section(self):
        service = ContextAssemblyService()
        chunk = _make_chunk(
            title="Alcazar de Sevilla",
            heritage_type="patrimonio_inmueble",
            province="Sevilla",
            content="Palacio real mudejar.",
            url="https://guiadigital.iaph.es/alcazar",
        )
        result = service.assemble([chunk])

        assert "[1] Alcazar de Sevilla (patrimonio_inmueble, Sevilla)" in result
        assert "Palacio real mudejar." in result
        assert "Fuente: https://guiadigital.iaph.es/alcazar" in result

    def test_multiple_chunks_separated_by_delimiter(self):
        service = ContextAssemblyService()
        chunks = [
            _make_chunk(title="Monumento A", chunk_id="c1"),
            _make_chunk(title="Monumento B", chunk_id="c2"),
        ]
        result = service.assemble(chunks)

        assert "\n---\n" in result
        assert "[1] Monumento A" in result
        assert "[2] Monumento B" in result

    def test_section_numbering_starts_at_one(self):
        service = ContextAssemblyService()
        chunks = [
            _make_chunk(title="Primero", chunk_id="c1"),
            _make_chunk(title="Segundo", chunk_id="c2"),
            _make_chunk(title="Tercero", chunk_id="c3"),
        ]
        result = service.assemble(chunks)

        assert "[1] Primero" in result
        assert "[2] Segundo" in result
        assert "[3] Tercero" in result

    def test_section_contains_all_metadata_fields(self):
        service = ContextAssemblyService()
        chunk = _make_chunk(
            title="La Alhambra",
            heritage_type="BIC",
            province="Granada",
            content="Complejo palaciego nazari.",
            url="https://guiadigital.iaph.es/alhambra",
        )
        result = service.assemble([chunk])

        lines = result.split("\n")
        # First line: header with title, heritage_type, province
        assert lines[0] == "[1] La Alhambra (BIC, Granada)"
        # Second line: content
        assert lines[1] == "Complejo palaciego nazari."
        # Third line: source URL
        assert lines[2] == "Fuente: https://guiadigital.iaph.es/alhambra"

    def test_no_trailing_delimiter(self):
        service = ContextAssemblyService()
        chunks = [
            _make_chunk(title="A", chunk_id="c1"),
            _make_chunk(title="B", chunk_id="c2"),
        ]
        result = service.assemble(chunks)

        assert not result.endswith("---")
        assert not result.endswith("---\n")
