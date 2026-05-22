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
    - "v6": natural-language templates literally following Samuel's
      (UJA) spec — driven by the dotted-key fields of the new JSONL
      format with strict field-level OMISSION (missing/empty fields drop
      the whole surrounding sentence)
    - "v4": legacy natural-language templates per heritage type (parquet
      schema)
    - anything else: pipe-separated metadata header
    """

    def __init__(self, chunks_version: str = "v1") -> None:
        self._chunks_version = chunks_version

    def enrich(self, document: Document, chunk: Chunk) -> EnrichedContent:
        if self._chunks_version == "v6":
            text = self._enrich_v6(document, chunk.content)
        elif self._chunks_version == "v4":
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

    # ------------------------------------------------------------------
    # v6 — Samuel's (UJA) plantillas RAG, literal
    # ------------------------------------------------------------------
    #
    # The v6 templates follow ``data/iaph_nuevo/README.md`` exactly. The
    # source metadata uses dotted keys (e.g. ``identifica.municipio_s``,
    # ``tipologia.materiales.den_tipologia_smv``) that are stored as
    # flat keys in ``Document.metadata``.
    #
    # OMISSION RULE: if a field is missing, ``None``, empty, blank, or
    # an array containing only blanks, the *entire* sentence that would
    # render it is dropped. We never emit "Su tipología es ." with an
    # empty placeholder.
    #
    # When a field is a list, items are joined with ", "; lists composed
    # solely of blank strings are treated as missing.

    @staticmethod
    def _v6_value(document: Document, key: str) -> str | None:
        """Look up a dotted/flat key in metadata and return a render-ready
        string, or ``None`` if the field should be omitted entirely."""
        if key not in document.metadata:
            return None
        value = document.metadata[key]
        if value is None:
            return None

        if isinstance(value, list):
            parts = [str(item).strip() for item in value if item is not None]
            parts = [p for p in parts if p and p.lower() != "nan"]
            if not parts:
                return None
            return ", ".join(parts)

        text = str(value).strip()
        if not text or text.lower() == "nan":
            return None
        return text

    def _v6_sentence(
        self, document: Document, template: str, *keys: str
    ) -> str | None:
        """Render a sentence template using one or more metadata keys.

        Returns ``None`` if any required key is missing/empty so the
        whole sentence is dropped per the OMISSION rule.
        """
        values: list[str] = []
        for key in keys:
            value = self._v6_value(document, key)
            if value is None:
                return None
            values.append(value)
        return template.format(*values)

    def _v6_raw(self, document: Document, key: str) -> str | None:
        """Return a pre-rendered natural-language field verbatim
        (e.g. ``proteccion``, ``ambito_desarrollo``, ``fuentes``).

        Used for fields that are already a full sentence in the source
        JSONL — they are emitted as-is when present, dropped otherwise.
        """
        return self._v6_value(document, key)

    def _enrich_v6(self, document: Document, content: str) -> str:
        ht = document.heritage_type
        if ht == HeritageType.PAISAJE_CULTURAL:
            return self._template_v6_paisaje(document, content)
        if ht == HeritageType.PATRIMONIO_INMATERIAL:
            return self._template_v6_inmaterial(document, content)
        if ht == HeritageType.PATRIMONIO_INMUEBLE:
            return self._template_v6_inmueble(document, content)
        if ht == HeritageType.PATRIMONIO_MUEBLE:
            return self._template_v6_mueble(document, content)
        return self._enrich_header(document, content)

    def _template_v6_inmueble(self, document: Document, content: str) -> str:
        sentences: list[str] = []

        denominacion = self._v6_value(document, "denominacion") or document.title
        if denominacion:
            sentences.append(f"Este bien inmueble se denomina '{denominacion}'.")

        s = self._v6_sentence(document, "Es de naturaleza {0}.", "caracterizacion")
        if s:
            sentences.append(s)

        municipio = self._v6_value(document, "identifica.municipio_s")
        provincia = self._v6_value(document, "identifica.provincia_s")
        if municipio and provincia:
            sentences.append(f"Está ubicado en {municipio}, provincia de {provincia}.")
        elif municipio:
            sentences.append(f"Está ubicado en {municipio}.")
        elif provincia:
            sentences.append(f"Está ubicado en la provincia de {provincia}.")

        s = self._v6_sentence(document, "Su tipología es {0}.", "tipologia_smv")
        if s:
            sentences.append(s)

        s = self._v6_sentence(
            document,
            "Se le puede asociar a la actividad {0}.",
            "tipologia.denom_acti_smv",
        )
        if s:
            sentences.append(s)

        s = self._v6_sentence(
            document, "Se sitúa en el periodo histórico {0}.", "pHistorico_smv"
        )
        if s:
            sentences.append(s)

        proteccion = self._v6_raw(document, "proteccion")
        if proteccion:
            sentences.append(proteccion)

        dat_historico = self._v6_value(document, "identifica.dat_historico_s")
        if dat_historico:
            sentences.append(dat_historico)

        s = self._v6_sentence(
            document,
            "Se puede consultar sus fuentes en {0}.",
            "bibliografia.titulo_smv",
        )
        if s:
            sentences.append(s)

        s = self._v6_sentence(
            document,
            "Sus fuentes también se pueden consultar en {0}.",
            "documental.uni_docs_smv",
        )
        if s:
            sentences.append(s)

        text = self._v6_value(document, "text") or content
        if text:
            sentences.append(text)

        return " ".join(sentences)

    def _template_v6_inmaterial(self, document: Document, content: str) -> str:
        sentences: list[str] = []

        denominacion = self._v6_value(document, "denominacion") or document.title
        if denominacion:
            sentences.append(f"Este bien inmaterial se denomina '{denominacion}'.")

        s = self._v6_sentence(
            document, "Pertenece al ámbito {0}.", "identifica.ambito_s"
        )
        if s:
            sentences.append(s)

        municipio = self._v6_value(document, "identifica.municipio_s")
        comarca = self._v6_value(document, "identifica.comarca_s")
        provincia = self._v6_value(document, "identifica.provincia_s")
        location_parts: list[str] = []
        if municipio:
            location_parts.append(f"municipio {municipio}")
        if comarca:
            location_parts.append(f"comarca {comarca}")
        if provincia:
            location_parts.append(f"provincia de {provincia}")
        if location_parts:
            sentences.append("Está ubicado en el " + ", ".join(location_parts) + ".")

        s = self._v6_sentence(
            document, "Se le atribuye la tipología {0}.", "identifica.tipologias_s"
        )
        if s:
            sentences.append(s)

        s = self._v6_sentence(
            document, "Se enmarca en la actividad {0}.", "identifica.actmarco_s"
        )
        if s:
            sentences.append(s)

        s = self._v6_sentence(
            document, "Sucede en las fechas de {0}.", "identifica.fechasact_s"
        )
        if s:
            sentences.append(s)

        s = self._v6_sentence(
            document, "Tiene una periodicidad {0}.", "identifica.periodicidad_s"
        )
        if s:
            sentences.append(s)

        actividad_rel = self._v6_raw(document, "actividadrelacionada.descripcion_smv")
        if actividad_rel:
            sentences.append(actividad_rel)

        ambito_desarrollo = self._v6_raw(document, "ambito_desarrollo")
        if ambito_desarrollo:
            sentences.append(ambito_desarrollo)

        s = self._v6_sentence(
            document,
            "Se puede consultar sus fuentes en {0}.",
            "bibliografia.titulo_smv",
        )
        if s:
            sentences.append(s)

        s = self._v6_sentence(
            document,
            "Sus fuentes también se pueden consultar en {0}.",
            "documental.uni_docs_smv",
        )
        if s:
            sentences.append(s)

        text = self._v6_value(document, "text") or content
        if text:
            sentences.append(text)

        return " ".join(sentences)

    def _template_v6_paisaje(self, document: Document, content: str) -> str:
        sentences: list[str] = []

        titulo = self._v6_value(document, "titulo") or document.title
        provincia = self._v6_value(document, "provincia")
        area = self._v6_value(document, "area")
        ambito = self._v6_value(document, "ambito")
        demarcacion = self._v6_value(document, "demarcacion_paisajistica")

        # The opening sentence in Samuel's spec interleaves up to four
        # location fields. We render only the fragments whose field is
        # present so the OMISSION rule is honoured at fragment level.
        if titulo:
            head = f"El '{titulo}' se localiza"
            fragments: list[str] = []
            if provincia:
                fragments.append(f"en la provincia de {provincia}")
            if area:
                fragments.append(f"dentro del área {area}")
            if ambito:
                fragments.append(f"en el ámbito {ambito}")
            if demarcacion:
                fragments.append(
                    f"pertenece a la demarcación paisajística {demarcacion}"
                )
            if fragments:
                sentences.append(head + " " + ", ".join(fragments) + ".")
            else:
                sentences.append(head + ".")

        text = self._v6_value(document, "text") or content
        if text:
            sentences.append(text)

        return " ".join(sentences)

    def _template_v6_mueble(self, document: Document, content: str) -> str:
        sentences: list[str] = []

        denominacion = (
            self._v6_value(document, "identifica.denominacion_s") or document.title
        )
        if denominacion:
            sentences.append(f"Este bien mueble se denomina {denominacion}.")

        s = self._v6_sentence(
            document, "Se caracteriza como {0}.", "identifica.caracterizacion_s"
        )
        if s:
            sentences.append(s)

        s = self._v6_sentence(
            document, "Está datado entre {0}.", "identifica.cronologia_s"
        )
        if s:
            sentences.append(s)

        s = self._v6_sentence(
            document, "Posee unas medidas {0}.", "identifica.medidas_s"
        )
        if s:
            sentences.append(s)

        municipio = self._v6_value(document, "identifica.municipio_s")
        provincia = self._v6_value(document, "identifica.provincia_s")
        if municipio and provincia:
            sentences.append(
                f"Se conserva en {municipio}, provincia de {provincia}."
            )
        elif municipio:
            sentences.append(f"Se conserva en {municipio}.")
        elif provincia:
            sentences.append(f"Se conserva en la provincia de {provincia}.")

        s = self._v6_sentence(
            document,
            "Está realizado con materiales como {0}.",
            "tipologia.materiales.den_tipologia_smv",
        )
        if s:
            sentences.append(s)

        s = self._v6_sentence(
            document,
            "Se asocia a las técnicas {0}.",
            "tipologia.tecnica.den_tipologia_smv",
        )
        if s:
            sentences.append(s)

        s = self._v6_sentence(
            document,
            "Se asocia a las tipologías {0}.",
            "tipologia.tipologias.den_tipologia_smv",
        )
        if s:
            sentences.append(s)

        s = self._v6_sentence(
            document,
            "Se atribuye al periodo {0}.",
            "tipologia.pHistorico.den_tipologia_smv",
        )
        if s:
            sentences.append(s)

        s = self._v6_sentence(
            document,
            "Pertenece a la escuela {0}.",
            "tipologia.escuelas.den_tipologia_smv",
        )
        if s:
            sentences.append(s)

        s = self._v6_sentence(
            document,
            "Es de estilo {0}.",
            "tipologia.estilos.den_tipologia_smv",
        )
        if s:
            sentences.append(s)

        s = self._v6_sentence(
            document,
            "Representa a la iconografía {0}.",
            "tipologia.iconografias.den_tipologia_smv",
        )
        if s:
            sentences.append(s)

        # Autor (Zurbarán fix): MUST be included for mueble.
        s = self._v6_sentence(
            document, "Su autoría se atribuye a {0}.", "agente.nombre_age_smv"
        )
        if s:
            sentences.append(s)

        s = self._v6_sentence(
            document,
            "El autor pertenece al colectivo de {0}.",
            "agente.tipo_agen_smv",
        )
        if s:
            sentences.append(s)

        proteccion = self._v6_raw(document, "proteccion")
        if proteccion:
            sentences.append(proteccion)

        fuentes = self._v6_raw(document, "fuentes")
        if fuentes:
            sentences.append(fuentes)

        dat_historico = self._v6_value(document, "identifica.dat_historico_s")
        if dat_historico:
            sentences.append(dat_historico)

        text = self._v6_value(document, "text") or content
        if text:
            sentences.append(text)

        return " ".join(sentences)
