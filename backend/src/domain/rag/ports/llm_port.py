from abc import ABC, abstractmethod

from src.domain.rag.entities.retrieved_chunk import RetrievedChunk


class LLMPort(ABC):
    """Port for LLM text generation."""

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context_chunks: list[RetrievedChunk],
    ) -> str:
        ...
