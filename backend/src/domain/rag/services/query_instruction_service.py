"""Instruction prefix wrapper for instruction-aware embedding models (e.g. Qwen3)."""


def wrap_query_for_embedding(query: str, instruction: str) -> str:
    """Wrap a query with the Qwen3-style instruction prefix.

    When *instruction* is non-empty the returned string follows the format
    expected by instruction-aware encoders::

        Instruct: {instruction}
        Query: {query}

    When *instruction* is empty or ``None``, the raw query is returned
    unchanged (backward-compatible with symmetric encoders like MrBERT).
    """
    if not instruction:
        return query
    return f"Instruct: {instruction}\nQuery: {query}"
