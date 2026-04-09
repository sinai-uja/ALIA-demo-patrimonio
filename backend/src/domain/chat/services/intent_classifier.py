import logging
from enum import StrEnum

from src.domain.chat.entities.message import Message
from src.domain.chat.entities.message_role import MessageRole
from src.domain.chat.ports.llm_port import ConversationalLLMPort
from src.domain.chat.prompts import INTENT_SYSTEM_PROMPT, build_intent_prompt

logger = logging.getLogger("iaph.chat.intent")

_HISTORY_WINDOW = 4

_INTENT_MAP = {
    "SALUDO": "conversational",
    "CONSULTA": "rag_query",
    "SEGUIMIENTO": "contextual_rag",
}


class MessageIntent(StrEnum):
    CONVERSATIONAL = "conversational"
    RAG_QUERY = "rag_query"
    CONTEXTUAL_RAG = "contextual_rag"


class IntentClassifier:
    """Classifies user messages using the LLM with a keyword prompt."""

    def __init__(self, llm_port: ConversationalLLMPort) -> None:
        self._llm_port = llm_port

    async def classify(self, message: str, history: list[Message]) -> MessageIntent:
        history_summary = self._summarize_history(history)
        user_prompt = build_intent_prompt(message, history_summary)

        response = await self._llm_port.generate(INTENT_SYSTEM_PROMPT, user_prompt)
        intent = self._parse_response(response)
        logger.info("Intent classified: %s (raw: %s)", intent.value, response.strip()[:30])
        return intent

    @staticmethod
    def _parse_response(response: str) -> MessageIntent:
        first_word = response.strip().split()[0].upper().rstrip(".:,;") if response.strip() else ""
        intent_value = _INTENT_MAP.get(first_word)
        if intent_value:
            return MessageIntent(intent_value)
        return MessageIntent.RAG_QUERY

    @staticmethod
    def _summarize_history(history: list[Message]) -> str:
        if not history:
            return "(sin historial)"

        recent = history[-_HISTORY_WINDOW:]
        lines = []
        for msg in recent:
            role = "Usuario" if msg.role == MessageRole.USER else "Asistente"
            content = msg.content[:100]
            lines.append(f"{role}: {content}")
        return "\n".join(lines)
