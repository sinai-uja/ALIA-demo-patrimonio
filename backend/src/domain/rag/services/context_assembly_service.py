from src.domain.rag.entities.retrieved_chunk import RetrievedChunk


class ContextAssemblyService:
    """Assembles retrieved chunks into a formatted context string for the LLM."""

    def assemble(self, chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return ""

        sections: list[str] = []
        for idx, chunk in enumerate(chunks, start=1):
            section = (
                f"[{idx}] {chunk.title} ({chunk.heritage_type}, {chunk.province})\n"
                f"{chunk.content}\n"
                f"Fuente: {chunk.url}"
            )
            sections.append(section)

        return "\n---\n".join(sections)
