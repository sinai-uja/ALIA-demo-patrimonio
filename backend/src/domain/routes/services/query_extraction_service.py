import re


class QueryExtractionService:
    """Cleans user text by removing geographic filter terms."""

    def clean_query_text(
        self,
        user_text: str,
        province_filters: list[str] | None = None,
        municipality_filters: list[str] | None = None,
    ) -> str:
        clean = user_text
        for terms in (province_filters, municipality_filters):
            if not terms:
                continue
            for term in terms:
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                clean = pattern.sub("", clean)
        clean = re.sub(r"\s{2,}", " ", clean).strip()
        clean = re.sub(
            r"\b(de|del|en|por|a)\s*$",
            "",
            clean,
            flags=re.IGNORECASE,
        ).strip()
        clean = re.sub(
            r"\b(de|del|en|por|a)\s+(de|del|en|por|a)\b",
            lambda m: m.group(1),
            clean,
            flags=re.IGNORECASE,
        ).strip()
        return clean
