import re
import unicodedata

from src.domain.search.entities.search_suggestion import DetectedEntity

# Mapping from keywords to heritage type identifiers
HERITAGE_TYPE_KEYWORDS: dict[str, str] = {
    "inmueble": "patrimonio_inmueble",
    "arquitectura": "patrimonio_inmueble",
    "edificio": "patrimonio_inmueble",
    "monumento": "patrimonio_inmueble",
    "iglesia": "patrimonio_inmueble",
    "castillo": "patrimonio_inmueble",
    "palacio": "patrimonio_inmueble",
    "mueble": "patrimonio_mueble",
    "objeto": "patrimonio_mueble",
    "escultura": "patrimonio_mueble",
    "pintura": "patrimonio_mueble",
    "retablo": "patrimonio_mueble",
    "inmaterial": "patrimonio_inmaterial",
    "fiesta": "patrimonio_inmaterial",
    "tradicion": "patrimonio_inmaterial",
    "rito": "patrimonio_inmaterial",
    "paisaje cultural": "paisaje_cultural",
    "paisaje": "paisaje_cultural",
}

HERITAGE_TYPE_LABELS: dict[str, str] = {
    "patrimonio_inmueble": "Patrimonio Inmueble",
    "patrimonio_mueble": "Patrimonio Mueble",
    "patrimonio_inmaterial": "Patrimonio Inmaterial",
    "paisaje_cultural": "Paisaje Cultural",
}

# Map base chars to patterns matching with or without accents
_ACCENT_MAP: dict[str, str] = {
    "a": "[aáàâä]",
    "e": "[eéèêë]",
    "i": "[iíìîï]",
    "o": "[oóòôö]",
    "u": "[uúùûü]",
    "n": "[nñ]",
    "c": "[cç]",
}


def _strip_accents(text: str) -> str:
    """Remove accents from text."""
    nfkd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn")


def _accent_insensitive_pattern(needle: str) -> str:
    """Build a regex pattern that matches needle ignoring accents."""
    parts: list[str] = []
    for ch in needle.lower():
        parts.append(_ACCENT_MAP.get(ch, re.escape(ch)))
    return r"\b" + "".join(parts) + r"\b"


def _find_match_in_query(needle_normalized: str, query: str) -> str | None:
    """Find needle (accent-stripped, lowercase) in the original query.

    Returns the matched substring from the original query preserving
    the user's casing and accents, or None if not found.
    """
    pattern = _accent_insensitive_pattern(needle_normalized)
    m = re.search(pattern, query, re.IGNORECASE)
    if m:
        return m.group(0)
    return None


class EntityDetectionService:
    """Stateless domain service that detects entities in search queries."""

    def detect(
        self,
        query: str,
        provinces: list[str],
        municipalities: list[str],
        heritage_types: list[str],
    ) -> list[DetectedEntity]:
        """Detect provinces, municipalities, and heritage types in a query."""
        query_normalized = _strip_accents(query.lower().strip())
        if not query_normalized:
            return []

        entities: list[DetectedEntity] = []
        seen_types: set[str] = set()

        # Detect heritage types via keyword mapping
        sorted_keywords = sorted(
            HERITAGE_TYPE_KEYWORDS.items(),
            key=lambda x: len(x[0]),
            reverse=True,
        )
        for keyword, heritage_type in sorted_keywords:
            if heritage_type in seen_types:
                continue
            norm_keyword = _strip_accents(keyword.lower())
            if re.search(r"\b" + re.escape(norm_keyword) + r"\b", query_normalized):
                label = HERITAGE_TYPE_LABELS.get(heritage_type, heritage_type)
                matched = _find_match_in_query(norm_keyword, query) or keyword
                entities.append(DetectedEntity(
                    entity_type="heritage_type",
                    value=heritage_type,
                    display_label=f"Tipo: {label}",
                    matched_text=matched,
                ))
                seen_types.add(heritage_type)

        # Detect provinces
        for province in provinces:
            norm_prov = _strip_accents(province.lower())
            if len(norm_prov) < 3:
                continue
            if re.search(r"\b" + re.escape(norm_prov) + r"\b", query_normalized):
                matched = _find_match_in_query(norm_prov, query) or province
                entities.append(DetectedEntity(
                    entity_type="province",
                    value=province,
                    display_label=f"Provincia: {province}",
                    matched_text=matched,
                ))

        # Detect municipalities (longer names first)
        sorted_municipalities = sorted(municipalities, key=len, reverse=True)
        detected_municipality_values: set[str] = set()
        for municipality in sorted_municipalities:
            norm_muni = _strip_accents(municipality.lower())
            if len(norm_muni) < 3:
                continue
            if re.search(r"\b" + re.escape(norm_muni) + r"\b", query_normalized):
                if municipality not in detected_municipality_values:
                    matched = _find_match_in_query(norm_muni, query) or municipality
                    entities.append(DetectedEntity(
                        entity_type="municipality",
                        value=municipality,
                        display_label=f"Municipio: {municipality}",
                        matched_text=matched,
                    ))
                    detected_municipality_values.add(municipality)

        return entities
