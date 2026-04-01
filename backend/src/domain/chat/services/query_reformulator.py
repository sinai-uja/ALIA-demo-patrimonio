import logging

from src.domain.chat.entities.message import Message
from src.domain.chat.entities.message_role import MessageRole

logger = logging.getLogger("iaph.query")

_STOPWORDS = {
    "de", "del", "la", "el", "los", "las", "un", "una", "en", "y", "a",
    "que", "qué", "es", "por", "con", "para", "al", "se", "lo", "como",
    "sobre", "hay", "me", "te", "nos", "les", "su", "mi", "tu",
    "dame", "dime", "hablame", "háblame", "cuentame", "cuéntame",
    "informacion", "información", "quiero", "saber", "necesito",
    "existen", "tiene", "tienen", "donde", "dónde", "cuales", "cuáles",
    "mas", "más", "otro", "otra", "otros", "otras", "ese", "esa",
    "esos", "esas", "cual", "cuál", "está", "esta", "relacionado",
    "relacionada", "son", "fue", "era", "ser", "haber", "hay",
}


class QueryReformulator:
    """Reformulates follow-up queries by injecting context from conversation history.

    Strategy: append the previous user query to provide full context,
    so the embedding model and text search capture the real intent.
    """

    def reformulate(self, current: str, history: list[Message]) -> str:
        last_user_query = self._find_last_user_query(history)
        if not last_user_query:
            return current

        # Combine current query with previous query for full context
        # e.g. "y en Málaga?" + prev "castillos en Jaén" → "castillos en Jaén y en Málaga?"
        reformulated = f"{last_user_query} — {current}"
        logger.info(
            "Query reformulated: '%s' + prev:'%s' → '%s'",
            current[:60], last_user_query[:60], reformulated[:120],
        )
        return reformulated

    @staticmethod
    def _find_last_user_query(history: list[Message]) -> str | None:
        for msg in reversed(history):
            if msg.role == MessageRole.USER:
                return msg.content
        return None
