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
    metadata: dict | None = None,
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
        metadata=metadata,
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
        # Second line: content (no metadata line for unknown heritage_type)
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


class TestMetadataEnrichment:
    """Tests for type-specific metadata inclusion in context assembly."""

    def test_inmueble_metadata_included(self):
        service = ContextAssemblyService()
        chunk = _make_chunk(
            heritage_type="patrimonio_inmueble",
            metadata={
                "characterisation": "Edificio",
                "type": "Catedral",
                "styles": "Renacentista",
                "historic_periods": "Edad Moderna",
                "protection": "BIC",
            },
        )
        result = service.assemble([chunk])

        assert "Naturaleza: Edificio" in result
        assert "Tipo: Catedral" in result
        assert "Estilo: Renacentista" in result
        assert "Periodo: Edad Moderna" in result
        assert "Proteccion: BIC" in result

    def test_mueble_metadata_included(self):
        service = ContextAssemblyService()
        chunk = _make_chunk(
            heritage_type="patrimonio_mueble",
            metadata={
                "type": "Retablo",
                "authors": "Pedro Dancart",
                "styles": "Gotico",
                "historic_periods": "Siglo XV",
                "materials": "Madera dorada",
                "techniques": "Talla",
            },
        )
        result = service.assemble([chunk])

        assert "Tipo: Retablo" in result
        assert "Autor: Pedro Dancart" in result
        assert "Estilo: Gotico" in result
        assert "Periodo: Siglo XV" in result
        assert "Material: Madera dorada" in result
        assert "Tecnica: Talla" in result

    def test_inmaterial_metadata_included(self):
        service = ContextAssemblyService()
        chunk = _make_chunk(
            heritage_type="patrimonio_inmaterial",
            metadata={
                "activity_types": "Festividad",
                "subject_topic": "Tradiciones religiosas",
            },
        )
        result = service.assemble([chunk])

        assert "Tipo actividad: Festividad" in result
        assert "Tema: Tradiciones religiosas" in result

    def test_paisaje_metadata_included(self):
        service = ContextAssemblyService()
        chunk = _make_chunk(
            heritage_type="paisaje_cultural",
            metadata={
                "topic": "Mineria",
                "landscape_demarcation": "Sierra Morena",
            },
        )
        result = service.assemble([chunk])

        assert "Tema: Mineria" in result
        assert "Demarcacion: Sierra Morena" in result

    def test_none_metadata_produces_no_metadata_line(self):
        service = ContextAssemblyService()
        chunk = _make_chunk(
            heritage_type="patrimonio_inmueble",
            metadata=None,
        )
        result = service.assemble([chunk])
        lines = result.split("\n")

        # Header line, then content directly (no metadata line in between)
        assert lines[0].startswith("[1]")
        assert lines[1] == "La catedral renacentista..."

    def test_empty_metadata_produces_no_metadata_line(self):
        service = ContextAssemblyService()
        chunk = _make_chunk(
            heritage_type="patrimonio_inmueble",
            metadata={},
        )
        result = service.assemble([chunk])
        lines = result.split("\n")

        assert lines[0].startswith("[1]")
        assert lines[1] == "La catedral renacentista..."

    def test_nan_values_are_skipped(self):
        service = ContextAssemblyService()
        chunk = _make_chunk(
            heritage_type="patrimonio_inmueble",
            metadata={
                "characterisation": "nan",
                "type": "Catedral",
                "styles": "",
                "historic_periods": None,
                "protection": "  ",
            },
        )
        result = service.assemble([chunk])

        assert "Naturaleza:" not in result
        assert "Estilo:" not in result
        assert "Periodo:" not in result
        assert "Proteccion:" not in result
        assert "Tipo: Catedral" in result

    def test_metadata_line_is_pipe_separated(self):
        service = ContextAssemblyService()
        chunk = _make_chunk(
            heritage_type="patrimonio_inmueble",
            metadata={
                "characterisation": "Edificio",
                "type": "Catedral",
            },
        )
        result = service.assemble([chunk])

        assert "Naturaleza: Edificio | Tipo: Catedral" in result

    def test_metadata_respects_char_budget(self):
        service = ContextAssemblyService(max_context_chars=200)
        chunks = [
            _make_chunk(
                title="Chunk A",
                chunk_id="c1",
                content="Contenido del primer chunk.",
                heritage_type="patrimonio_mueble",
                metadata={
                    "type": "Retablo",
                    "authors": "Autor largo para ocupar espacio en el budget",
                    "styles": "Gotico",
                },
            ),
            _make_chunk(
                title="Chunk B",
                chunk_id="c2",
                content="Contenido del segundo chunk.",
                heritage_type="patrimonio_mueble",
                metadata={"type": "Escultura"},
            ),
        ]
        result = service.assemble(chunks)

        assert len(result) <= 200 or "[2]" not in result

    def test_metadata_on_all_chunks_of_same_document(self):
        """All chunks from a document should carry the same metadata context."""
        service = ContextAssemblyService()
        meta = {
            "characterisation": "Edificio",
            "type": "Catedral",
            "styles": "Renacentista",
        }
        chunks = [
            _make_chunk(
                chunk_id="c1",
                content="Primer fragmento del documento.",
                metadata=meta,
            ),
            _make_chunk(
                chunk_id="c2",
                content="Segundo fragmento del documento.",
                metadata=meta,
            ),
            _make_chunk(
                chunk_id="c3",
                content="Tercer fragmento del documento.",
                metadata=meta,
            ),
        ]
        result = service.assemble(chunks)

        # Each chunk section should contain the metadata line
        assert result.count("Naturaleza: Edificio") == 3
        assert result.count("Tipo: Catedral") == 3
        assert result.count("Estilo: Renacentista") == 3
