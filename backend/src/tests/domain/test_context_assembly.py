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


class TestContextAssemblyRawContent:
    """Tests for chunks with raw content (v1/v2/v3 — title NOT in content)."""

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
        assert lines[0] == "[1] La Alhambra (BIC, Granada)"
        assert lines[1] == "Complejo palaciego nazari."
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


class TestMetadataEnrichmentRawContent:
    """Tests for metadata line injection on raw content chunks (v3 with JSONB)."""

    def test_inmueble_metadata_included(self):
        service = ContextAssemblyService()
        chunk = _make_chunk(
            heritage_type="patrimonio_inmueble",
            content="Texto crudo sin titulo.",
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
            content="Texto crudo sin titulo.",
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
        assert "Material: Madera dorada" in result

    def test_inmaterial_metadata_included(self):
        service = ContextAssemblyService()
        chunk = _make_chunk(
            heritage_type="patrimonio_inmaterial",
            content="Texto crudo sin titulo.",
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
            content="Texto crudo sin titulo.",
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
            content="Texto crudo sin titulo.",
            metadata=None,
        )
        result = service.assemble([chunk])
        lines = result.split("\n")

        assert lines[0].startswith("[1]")
        assert lines[1] == "Texto crudo sin titulo."

    def test_empty_metadata_produces_no_metadata_line(self):
        service = ContextAssemblyService()
        chunk = _make_chunk(
            heritage_type="patrimonio_inmueble",
            content="Texto crudo sin titulo.",
            metadata={},
        )
        result = service.assemble([chunk])
        lines = result.split("\n")

        assert lines[0].startswith("[1]")
        assert lines[1] == "Texto crudo sin titulo."

    def test_nan_values_are_skipped(self):
        service = ContextAssemblyService()
        chunk = _make_chunk(
            heritage_type="patrimonio_inmueble",
            content="Texto crudo sin titulo.",
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
            content="Texto crudo sin titulo.",
            metadata={
                "characterisation": "Edificio",
                "type": "Catedral",
            },
        )
        result = service.assemble([chunk])

        assert "Naturaleza: Edificio | Tipo: Catedral" in result

    def test_metadata_on_all_raw_chunks_of_same_document(self):
        """All raw chunks from a document should carry the metadata line."""
        service = ContextAssemblyService()
        meta = {
            "characterisation": "Edificio",
            "type": "Catedral",
            "styles": "Renacentista",
        }
        chunks = [
            _make_chunk(
                chunk_id="c1",
                content="Primer fragmento.",
                metadata=meta,
            ),
            _make_chunk(
                chunk_id="c2",
                content="Segundo fragmento.",
                metadata=meta,
            ),
            _make_chunk(
                chunk_id="c3",
                content="Tercer fragmento.",
                metadata=meta,
            ),
        ]
        result = service.assemble(chunks)

        assert result.count("Naturaleza: Edificio") == 3
        assert result.count("Tipo: Catedral") == 3


class TestEnrichedContent:
    """Tests for chunks with enriched content (v4 — title already in content)."""

    def test_enriched_chunk_skips_header_and_metadata(self):
        """When content already contains the title, skip duplicate header."""
        service = ContextAssemblyService()
        enriched = (
            "Bien inmueble titulado 'Catedral de Jaen'. "
            "Es una propiedad de naturaleza Edificio y tipo Catedral. "
            "Ubicado en el municipio de Jaen, provincia de Jaen.\n"
            "La catedral renacentista fue construida sobre la antigua mezquita."
        )
        chunk = _make_chunk(
            title="Catedral de Jaen",
            heritage_type="patrimonio_inmueble",
            province="Jaen",
            content=enriched,
            metadata={"characterisation": "Edificio", "type": "Catedral"},
        )
        result = service.assemble([chunk])

        # Should NOT have the header line with "(patrimonio_inmueble, Jaen)"
        assert "(patrimonio_inmueble, Jaen)" not in result
        # Should NOT have the pipe-separated metadata line
        assert "Naturaleza: Edificio | Tipo: Catedral" not in result
        # Should have the enriched content directly after [1]
        assert "[1] Bien inmueble titulado" in result
        assert "Fuente:" in result

    def test_enriched_chunk_keeps_numbering_and_source(self):
        service = ContextAssemblyService()
        enriched = (
            "Paisaje cultural titulado 'Vega de Granada' "
            "y ubicado en la provincia de 'Granada'.\n"
            "Extenso paisaje de la vega granadina."
        )
        chunk = _make_chunk(
            title="Vega de Granada",
            heritage_type="paisaje_cultural",
            province="Granada",
            content=enriched,
            url="https://guiadigital.iaph.es/vega-granada",
        )
        result = service.assemble([chunk])

        assert result.startswith("[1] Paisaje cultural titulado")
        assert "Fuente: https://guiadigital.iaph.es/vega-granada" in result

    def test_multiple_enriched_chunks_all_have_context(self):
        """All enriched chunks carry their metadata in content."""
        service = ContextAssemblyService()
        enriched_template = (
            "Bien inmueble titulado 'Catedral de Jaen'. "
            "Ubicado en Jaen.\n{text}"
        )
        chunks = [
            _make_chunk(
                chunk_id="c1",
                content=enriched_template.format(text="Primer fragmento."),
            ),
            _make_chunk(
                chunk_id="c2",
                content=enriched_template.format(text="Segundo fragmento."),
            ),
            _make_chunk(
                chunk_id="c3",
                content=enriched_template.format(text="Tercer fragmento."),
            ),
        ]
        result = service.assemble(chunks)

        # All 3 chunks should have enriched content (title in content)
        assert result.count("Bien inmueble titulado 'Catedral de Jaen'") == 3
        # None should have the old-style header
        assert "(patrimonio_inmueble, Jaen)" not in result

    def test_mixed_enriched_and_raw_chunks(self):
        """Mix of v4 (enriched) and v3 (raw) chunks in same assembly."""
        service = ContextAssemblyService()
        enriched = (
            "Bien inmueble titulado 'Catedral de Jaen'. Ubicado en Jaen.\n"
            "Primer fragmento enriquecido."
        )
        chunks = [
            _make_chunk(
                title="Catedral de Jaen",
                chunk_id="c1",
                content=enriched,
            ),
            _make_chunk(
                title="Alcazar de Sevilla",
                chunk_id="c2",
                content="Texto crudo del alcazar.",
            ),
        ]
        result = service.assemble(chunks)

        # First chunk: enriched, no header duplication
        assert "[1] Bien inmueble titulado" in result
        # Second chunk: raw, has header
        assert "[2] Alcazar de Sevilla (patrimonio_inmueble, Jaen)" in result

    def test_enriched_chunk_respects_char_budget(self):
        service = ContextAssemblyService(max_context_chars=150)
        enriched = (
            "Bien inmueble titulado 'Catedral de Jaen'. "
            "Ubicado en Jaen.\n"
            "Un texto largo que ocupa bastante espacio en el budget de caracteres."
        )
        chunks = [
            _make_chunk(chunk_id="c1", content=enriched),
            _make_chunk(chunk_id="c2", content=enriched),
        ]
        result = service.assemble(chunks)

        assert "[1]" in result
        assert len(result) <= 150 or "[2]" not in result
