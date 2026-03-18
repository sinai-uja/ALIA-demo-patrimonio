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


def _normalize(text: str) -> str:
    """Normalize text: lowercase, strip accents."""
    text = text.lower().strip()
    nfkd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn")


def _word_boundary_match(needle: str, haystack: str) -> bool:
    """Check if needle appears as a whole word/phrase in haystack."""
    pattern = r"(?:^|\b)" + re.escape(needle) + r"(?:\b|$)"
    return bool(re.search(pattern, haystack))


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
        normalized_query = _normalize(query)
        if not normalized_query:
            return []

        entities: list[DetectedEntity] = []
        seen_types: set[str] = set()

        # Detect heritage types via keyword mapping
        # Check multi-word keywords first (e.g. "paisaje cultural")
        sorted_keywords = sorted(
            HERITAGE_TYPE_KEYWORDS.items(),
            key=lambda x: len(x[0]),
            reverse=True,
        )
        for keyword, heritage_type in sorted_keywords:
            if heritage_type in seen_types:
                continue
            if _word_boundary_match(_normalize(keyword), normalized_query):
                label = HERITAGE_TYPE_LABELS.get(
                    heritage_type, heritage_type,
                )
                entities.append(DetectedEntity(
                    entity_type="heritage_type",
                    value=heritage_type,
                    display_label=f"Tipo: {label}",
                    matched_text=keyword,
                ))
                seen_types.add(heritage_type)

        # Detect provinces (whole-word match to avoid false positives)
        for province in provinces:
            norm_prov = _normalize(province)
            if len(norm_prov) < 3:
                continue
            if _word_boundary_match(norm_prov, normalized_query):
                entities.append(DetectedEntity(
                    entity_type="province",
                    value=province,
                    display_label=f"Provincia: {province}",
                    matched_text=province,
                ))

        # Detect municipalities (whole-word match, longer names first)
        sorted_municipalities = sorted(
            municipalities, key=len, reverse=True,
        )
        detected_municipality_values: set[str] = set()
        for municipality in sorted_municipalities:
            norm_muni = _normalize(municipality)
            if len(norm_muni) < 3:
                continue
            if _word_boundary_match(norm_muni, normalized_query):
                if municipality not in detected_municipality_values:
                    entities.append(DetectedEntity(
                        entity_type="municipality",
                        value=municipality,
                        display_label=f"Municipio: {municipality}",
                        matched_text=municipality,
                    ))
                    detected_municipality_values.add(municipality)

        return entities
