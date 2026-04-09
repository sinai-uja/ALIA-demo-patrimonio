"""Domain service that enriches chunk content with document metadata.

The enriched text is what gets fed to the embedder so that the stored
vector reflects richer semantic information than the raw chunk body.

Pure domain: no IO, no infrastructure imports, no entity mutation.
"""

from dataclasses import dataclass

from src.domain.documents.entities.chunk import Chunk
from src.domain.documents.entities.document import Document
from src.domain.documents.value_objects.heritage_type import HeritageType

# Type-specific metadata fields to prepend to chunk content for richer
# embeddings (v2/v3). Each entry is (parquet_column_name, human_readable_label).
_ENRICHMENT_FIELDS: dict[HeritageType, list[tuple[str, str]]] = {
    HeritageType.PATRIMONIO_MUEBLE: [
        ("authors", "Autor"),
        ("styles", "Estilo"),
        ("historic_periods", "Periodo"),
        ("chronology", "Cronologia"),
        ("materials", "Material"),
        ("techniques", "Tecnica"),
        ("type", "Tipo bien"),
        ("protection", "Proteccion"),
        ("iconographies", "Iconografia"),
    ],
    HeritageType.PATRIMONIO_INMUEBLE: [
        ("characterisation", "Caracterizacion"),
        ("protection", "Proteccion"),
    ],
    HeritageType.PATRIMONIO_INMATERIAL: [
        ("activity_types", "Tipo actividad"),
        ("subject_topic", "Tema"),
    ],
    HeritageType.PAISAJE_CULTURAL: [
        ("topic", "Tema"),
        ("landscape_demarcation", "Demarcacion"),
    ],
}


@dataclass(frozen=True)
class EnrichedContent:
    """Immutable value object holding chunk text enriched for embedding."""

    text: str


class DocumentEnrichmentService:
    """Builds enriched chunk text (header or natural-language templates).

    The chunks_version controls the rendering strategy:
    - "v4": natural-language templates per heritage type
    - anything else: pipe-separated metadata header
    """

    def __init__(self, chunks_version: str = "v1") -> None:
        self._chunks_version = chunks_version

    def enrich(self, document: Document, chunk: Chunk) -> EnrichedContent:
        if self._chunks_version == "v4":
            text = self._enrich_v4(document, chunk.content)
        else:
            text = self._enrich_header(document, chunk.content)
        return EnrichedContent(text=text)

    @staticmethod
    def _enrich_header(document: Document, content: str) -> str:
        parts = [f"Titulo: {document.title}"]
        parts.append(f"Tipo: {document.heritage_type.value}")
        parts.append(f"Provincia: {document.province}")
        if document.municipality:
            parts.append(f"Municipio: {document.municipality}")

        for field_key, label in _ENRICHMENT_FIELDS.get(document.heritage_type, []):
            value = document.metadata.get(field_key)
            if value is not None and str(value).strip() and str(value).lower() != "nan":
                parts.append(f"{label}: {value}")

        header = " | ".join(parts)
        return f"{header}\n---\n{content}"

    @staticmethod
    def _get_meta(document: Document, key: str) -> str | None:
        value = document.metadata.get(key)
        if value is None or str(value).strip() == "" or str(value).lower() == "nan":
            return None
        return str(value).strip()

    def _enrich_v4(self, document: Document, content: str) -> str:
        ht = document.heritage_type
        if ht == HeritageType.PAISAJE_CULTURAL:
            return self._template_paisaje(document, content)
        if ht == HeritageType.PATRIMONIO_INMATERIAL:
            return self._template_inmaterial(document, content)
        if ht == HeritageType.PATRIMONIO_INMUEBLE:
            return self._template_inmueble(document, content)
        if ht == HeritageType.PATRIMONIO_MUEBLE:
            return self._template_mueble(document, content)
        return self._enrich_header(document, content)

    def _template_paisaje(self, document: Document, content: str) -> str:
        header = (
            f"Paisaje cultural titulado '{document.title}' "
            f"y ubicado en la provincia de '{document.province}'."
        )
        return f"{header}\n{content}"

    def _template_inmaterial(self, document: Document, content: str) -> str:
        activity_types = self._get_meta(document, "activity_types")
        subject_topic = self._get_meta(document, "subject_topic")
        district = self._get_meta(document, "district")
        municipality = document.municipality
        province = document.province

        parts = [f"Bien inmaterial titulado '{document.title}'"]
        if activity_types and subject_topic:
            parts[0] += f", clasificado como {activity_types} bajo la categoría {subject_topic}"
        elif activity_types:
            parts[0] += f", clasificado como {activity_types}"
        elif subject_topic:
            parts[0] += f", de categoría {subject_topic}"
        parts[0] += "."

        location_parts = [p for p in [district, municipality, province] if p]
        if location_parts:
            parts.append(f"Ubicado en {', '.join(location_parts)}.")

        header = " ".join(parts)
        return f"{header}\n{content}"

    def _template_inmueble(self, document: Document, content: str) -> str:
        characterisation = self._get_meta(document, "characterisation")
        type_val = self._get_meta(document, "type")
        municipality = document.municipality
        province = document.province
        style = self._get_meta(document, "styles")
        historic_periods = self._get_meta(document, "historic_periods")

        line1 = f"Bien inmueble titulado '{document.title}'."
        if characterisation and type_val:
            line1 = (
                f"Bien inmueble titulado '{document.title}'. "
                f"Es una propiedad de naturaleza {characterisation} y tipo {type_val}."
            )
        elif characterisation:
            line1 = (
                f"Bien inmueble titulado '{document.title}'. "
                f"Es una propiedad de naturaleza {characterisation}."
            )

        if municipality:
            line1 += f" Ubicado en el municipio de {municipality}, provincia de {province}."
        else:
            line1 += f" Ubicado en la provincia de {province}."

        lines = [line1]
        if style and historic_periods:
            lines.append(f"De estilo {style} y período histórico {historic_periods}.")
        elif style:
            lines.append(f"De estilo {style}.")
        elif historic_periods:
            lines.append(f"De período histórico {historic_periods}.")

        header = "\n".join(lines)
        return f"{header}\n{content}"

    def _template_mueble(self, document: Document, content: str) -> str:
        type_val = self._get_meta(document, "type")
        municipality = document.municipality
        province = document.province
        style = self._get_meta(document, "styles")
        historic_periods = self._get_meta(document, "historic_periods")

        if type_val:
            line1 = f"Bien mueble titulado '{document.title}' de tipo {type_val}."
        else:
            line1 = f"Bien mueble titulado '{document.title}'."

        if municipality:
            line1 += f" Ubicado en el municipio de {municipality}, provincia de {province}."
        else:
            line1 += f" Ubicado en la provincia de {province}."

        lines = [line1]
        if style and historic_periods:
            lines.append(f"De estilo {style} y período histórico {historic_periods}.")
        elif style:
            lines.append(f"De estilo {style}.")
        elif historic_periods:
            lines.append(f"De período histórico {historic_periods}.")

        header = "\n".join(lines)
        return f"{header}\n{content}"
