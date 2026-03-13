from abc import ABC, abstractmethod


class ConversationalLLMPort(ABC):
    """Port for generating conversational responses without RAG context."""

    @abstractmethod
    async def generate(self, system_prompt: str, user_message: str) -> str:
        """Generate a response using only the system prompt and user message."""
        ...
