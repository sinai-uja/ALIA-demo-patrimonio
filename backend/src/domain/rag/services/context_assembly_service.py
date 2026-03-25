from src.domain.rag.entities.retrieved_chunk import RetrievedChunk

# Type-specific metadata fields to include in context assembly.
# Maps heritage_type -> list of (json_key, label).
_CONTEXT_META_FIELDS: dict[str, list[tuple[str, str]]] = {
    "patrimonio_inmueble": [
        ("characterisation", "Naturaleza"),
        ("type", "Tipo"),
        ("styles", "Estilo"),
        ("historic_periods", "Periodo"),
        ("protection", "Proteccion"),
    ],
    "patrimonio_mueble": [
        ("type", "Tipo"),
        ("authors", "Autor"),
        ("styles", "Estilo"),
        ("historic_periods", "Periodo"),
        ("materials", "Material"),
        ("techniques", "Tecnica"),
    ],
    "patrimonio_inmaterial": [
        ("activity_types", "Tipo actividad"),
        ("subject_topic", "Tema"),
    ],
    "paisaje_cultural": [
        ("topic", "Tema"),
        ("landscape_demarcation", "Demarcacion"),
    ],
}


class ContextAssemblyService:
    """Assembles retrieved chunks into a formatted context string for the LLM.

    Enforces a max character budget to avoid exceeding the LLM context window.
    """

    def __init__(self, max_context_chars: int = 6000) -> None:
        self._max_chars = max_context_chars

    def assemble(self, chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return ""

        sections: list[str] = []
        total_chars = 0

        for idx, chunk in enumerate(chunks, start=1):
            # If content already contains the title, it was enriched at ingestion (v4)
            # — skip the header and metadata line to avoid duplication.
            if chunk.title in chunk.content:
                section = (
                    f"[{idx}] {chunk.content}\n"
                    f"Fuente: {chunk.url}"
                )
            else:
                meta_line = self._build_metadata_line(
                    chunk.heritage_type, chunk.metadata,
                )
                meta_part = f"{meta_line}\n" if meta_line else ""
                section = (
                    f"[{idx}] {chunk.title} ({chunk.heritage_type}, {chunk.province})\n"
                    f"{meta_part}"
                    f"{chunk.content}\n"
                    f"Fuente: {chunk.url}"
                )
            if total_chars + len(section) > self._max_chars and sections:
                break
            sections.append(section)
            total_chars += len(section)

        return "\n---\n".join(sections)

    @staticmethod
    def _get_meta(metadata: dict, key: str) -> str | None:
        """Extract a metadata value, returning None if missing or empty."""
        value = metadata.get(key)
        if value is None or str(value).strip() == "" or str(value).lower() == "nan":
            return None
        return str(value).strip()

    @classmethod
    def _build_metadata_line(cls, heritage_type: str, metadata: dict | None) -> str:
        """Build a compact pipe-separated metadata line from type-specific fields."""
        if not metadata:
            return ""
        fields = _CONTEXT_META_FIELDS.get(heritage_type, [])
        parts: list[str] = []
        for key, label in fields:
            value = cls._get_meta(metadata, key)
            if value:
                parts.append(f"{label}: {value}")
        return " | ".join(parts)
