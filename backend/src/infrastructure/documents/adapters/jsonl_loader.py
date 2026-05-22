"""JSONL document loader for the new IAPH dataset format (v6).

Each JSONL file contains one JSON object per line with structured fields
(see ``data/iaph_nuevo/README.md``). The loader streams the file line by
line so it can handle very large datasets (e.g. ``mueble.jsonl`` has
~107K records) without loading the whole file into memory.

The full record is preserved verbatim in ``Document.metadata`` so the
domain enrichment service can render the v6 natural-language templates
without losing dotted-key fields (``identifica.municipio_s``,
``tipologia.materiales.den_tipologia_smv``, ...).
"""

import json
import logging
from collections.abc import Iterator

from src.domain.documents.entities.document import Document
from src.domain.documents.ports.document_loader import DocumentLoader
from src.domain.documents.value_objects.heritage_type import HeritageType

logger = logging.getLogger("iaph.documents.jsonl_loader")

# Public IAPH digital guide URL pattern used as a stable fallback when no
# explicit ``url`` field is present in the source JSONL (the new format
# does not carry it). The dataset_id already encodes the heritage type
# and api_id, so we can synthesise a deterministic URL from it.
_GUIA_URL_TEMPLATE = "https://guiadigital.iaph.es/{tipo}/{api_id}"

# Map heritage type to the URL ``tipo`` path segment.
_URL_TIPO_BY_HERITAGE: dict[HeritageType, str] = {
    HeritageType.PAISAJE_CULTURAL: "paisaje",
    HeritageType.PATRIMONIO_INMATERIAL: "inmaterial",
    HeritageType.PATRIMONIO_INMUEBLE: "inmueble",
    HeritageType.PATRIMONIO_MUEBLE: "mueble",
}

# Map heritage type to the dataset_id ``tipo`` segment used when we have
# to rebuild a missing dataset_id from heritage_type + api_id. The format
# matches the v4/v5 document_id convention ``ficha-<tipo>-<api_id>`` so
# ingestion remains idempotent across schema versions and the
# ``heritage_assets`` FK keeps resolving.
_DATASET_TIPO_BY_HERITAGE: dict[HeritageType, str] = {
    HeritageType.PAISAJE_CULTURAL: "paisaje",
    HeritageType.PATRIMONIO_INMATERIAL: "inmaterial",
    HeritageType.PATRIMONIO_INMUEBLE: "inmueble",
    HeritageType.PATRIMONIO_MUEBLE: "mueble",
}


def _stringify(value: object) -> str | None:
    """Return a clean string for the given value, or ``None`` if blank.

    Used only when extracting Document entity fields. The full original
    value is still preserved verbatim inside ``metadata``.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def _extract_title(record: dict, heritage_type: HeritageType) -> str:
    """Pick the title for the document according to the heritage type."""
    if heritage_type == HeritageType.PAISAJE_CULTURAL:
        candidate = record.get("titulo")
    elif heritage_type == HeritageType.PATRIMONIO_MUEBLE:
        candidate = record.get("identifica.denominacion_s")
    else:  # inmueble / inmaterial
        candidate = record.get("denominacion")
    return _stringify(candidate) or ""


def _extract_province(record: dict, heritage_type: HeritageType) -> str:
    if heritage_type == HeritageType.PAISAJE_CULTURAL:
        candidate = record.get("provincia")
    else:
        candidate = record.get("identifica.provincia_s")
    return _stringify(candidate) or ""


def _extract_municipality(record: dict, heritage_type: HeritageType) -> str | None:
    if heritage_type == HeritageType.PAISAJE_CULTURAL:
        # Paisaje records do not carry municipality in the new format.
        return None
    return _stringify(record.get("identifica.municipio_s"))


def _extract_document_id(record: dict, heritage_type: HeritageType) -> str:
    """Return the canonical document id ``ficha-<tipo>-<api_id>``.

    Prefer ``dataset_id`` when present (it already follows this exact
    format in Samuel's JSONL), otherwise rebuild it from ``api_id``.
    """
    dataset_id = _stringify(record.get("dataset_id"))
    if dataset_id:
        return dataset_id

    api_id = _stringify(record.get("api_id"))
    if not api_id:
        return ""

    tipo = _DATASET_TIPO_BY_HERITAGE[heritage_type]
    return f"ficha-{tipo}-{api_id}"


def _extract_url(record: dict, heritage_type: HeritageType) -> str:
    """Return the URL field, synthesising a deterministic one if absent."""
    explicit = _stringify(record.get("url"))
    if explicit:
        return explicit

    api_id = _stringify(record.get("api_id"))
    if not api_id:
        return ""

    tipo = _URL_TIPO_BY_HERITAGE[heritage_type]
    return _GUIA_URL_TEMPLATE.format(tipo=tipo, api_id=api_id)


def _join_list_field(value: object) -> str | None:
    """Render a list/str field as a comma-joined plain string, or None."""
    if value is None:
        return None
    if isinstance(value, list):
        parts = [str(v).strip() for v in value if str(v).strip()]
        return ", ".join(parts) if parts else None
    text = str(value).strip()
    return text or None


def _synthesize_text_fallback(record: dict, heritage_type: HeritageType) -> str:
    """Build a minimal text body from key metadata when ``text`` is empty.

    The ChunkingService filters out documents whose ``text`` field is
    blank, which would drop ~16K mueble records that carry rich metadata
    (denomination, autor, materiales, etc.) but no narrative description.
    Providing a small but meaningful fallback body keeps those records
    indexable. The v6 enrichment template still wraps the full
    natural-language context around it, so the embedded chunk has all the
    structured fields available.

    Returns "" if no useful metadata is present, in which case the chunker
    will correctly drop the document.
    """
    parts: list[str] = []

    # Title / denomination — the single most-identifying field.
    if heritage_type == HeritageType.PAISAJE_CULTURAL:
        title = _stringify(record.get("titulo"))
    elif heritage_type == HeritageType.PATRIMONIO_MUEBLE:
        title = _stringify(record.get("identifica.denominacion_s"))
    else:
        title = _stringify(record.get("denominacion"))
    if title:
        parts.append(title)

    # Mueble-specific: add author and key tipology so a chunk is still
    # discoverable by author / school / iconography searches even without
    # a narrative body. Mirrors the Zurbarán case.
    if heritage_type == HeritageType.PATRIMONIO_MUEBLE:
        autor = _join_list_field(record.get("agente.nombre_age_smv"))
        if autor:
            parts.append(f"Autor: {autor}")
        for key, label in (
            ("tipologia.tipologias.den_tipologia_smv", "Tipología"),
            ("tipologia.escuelas.den_tipologia_smv", "Escuela"),
            ("tipologia.estilos.den_tipologia_smv", "Estilo"),
            ("tipologia.iconografias.den_tipologia_smv", "Iconografía"),
            ("tipologia.pHistorico.den_tipologia_smv", "Periodo"),
        ):
            value = _join_list_field(record.get(key))
            if value:
                parts.append(f"{label}: {value}")
    elif heritage_type == HeritageType.PATRIMONIO_INMUEBLE:
        caract = _stringify(record.get("caracterizacion"))
        if caract:
            parts.append(f"Caracterización: {caract}")
        tipologia = _join_list_field(record.get("tipologia_smv"))
        if tipologia:
            parts.append(f"Tipología: {tipologia}")
    elif heritage_type == HeritageType.PATRIMONIO_INMATERIAL:
        ambito = _stringify(record.get("identifica.ambito_s"))
        if ambito:
            parts.append(f"Ámbito: {ambito}")

    return " — ".join(parts)


class JsonlDocumentLoader(DocumentLoader):
    """Streams heritage documents from a JSONL file (one record per line).

    The entire record is kept inside ``Document.metadata`` so the
    enrichment service can render the v6 natural-language templates with
    direct lookups against dotted keys (e.g. ``identifica.municipio_s``).
    """

    def load_documents(
        self, source_path: str, heritage_type: HeritageType
    ) -> Iterator[Document]:
        try:
            file_handle = open(source_path, encoding="utf-8")
        except OSError:
            logger.error(
                "Failed to open JSONL file source_path=%r", source_path, exc_info=True
            )
            raise

        with file_handle as fh:
            for line_no, raw_line in enumerate(fh, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning(
                        "Skipping malformed JSONL line at %s:%d",
                        source_path,
                        line_no,
                    )
                    continue

                if not isinstance(record, dict):
                    logger.warning(
                        "Skipping non-object JSONL line at %s:%d", source_path, line_no
                    )
                    continue

                doc_id = _extract_document_id(record, heritage_type)
                if not doc_id:
                    logger.warning(
                        "Skipping JSONL record without dataset_id/api_id at %s:%d",
                        source_path,
                        line_no,
                    )
                    continue

                title = _extract_title(record, heritage_type)
                province = _extract_province(record, heritage_type)
                municipality = _extract_municipality(record, heritage_type)
                url = _extract_url(record, heritage_type)
                text = _stringify(record.get("text")) or ""

                # When the natural-language body is empty, fall back to a
                # synthesised body built from key metadata so the chunker
                # still emits a chunk for records that only carry
                # structured fields (~16K mueble records in the new IAPH
                # dataset). Skips the document only if NOTHING useful is
                # available.
                if not text:
                    text = _synthesize_text_fallback(record, heritage_type)

                yield Document(
                    id=doc_id,
                    url=url,
                    title=title,
                    province=province,
                    heritage_type=heritage_type,
                    text=text,
                    municipality=municipality,
                    # Preserve the full original payload (including
                    # dotted-key fields) so the enrichment service can
                    # render the v6 templates faithfully.
                    metadata=dict(record),
                )
