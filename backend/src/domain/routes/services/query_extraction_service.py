import re


class QueryExtractionService:
    """Cleans user text for query extraction."""

    def clean_query_text(
        self,
        user_text: str,
        province_filters: list[str] | None = None,
        municipality_filters: list[str] | None = None,
    ) -> str:
        """Normalize whitespace. Geographic terms are kept in the query
        because they carry semantic value for embedding search."""
        clean = re.sub(r"\s{2,}", " ", user_text).strip()
        return clean
