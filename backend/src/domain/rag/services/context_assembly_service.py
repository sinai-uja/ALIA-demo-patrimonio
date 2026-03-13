from src.domain.rag.entities.retrieved_chunk import RetrievedChunk


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
            section = (
                f"[{idx}] {chunk.title} ({chunk.heritage_type}, {chunk.province})\n"
                f"{chunk.content}\n"
                f"Fuente: {chunk.url}"
            )
            if total_chars + len(section) > self._max_chars and sections:
                break
            sections.append(section)
            total_chars += len(section)

        return "\n---\n".join(sections)
