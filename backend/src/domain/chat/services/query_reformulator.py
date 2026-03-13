import re

from src.domain.chat.entities.message import Message
from src.domain.chat.entities.message_role import MessageRole

_HERITAGE_KEYWORDS = {
    "castillo", "castillos", "iglesia", "iglesias", "patrimonio", "monumento",
    "monumentos", "mezquita", "mezquitas", "museo", "museos", "palacio", "palacios",
    "ermita", "ermitas", "torre", "torres", "muralla", "murallas", "puente",
    "puentes", "convento", "conventos", "catedral", "catedrales", "alcazaba",
    "fortaleza", "fortalezas", "yacimiento", "yacimientos", "capilla", "capillas",
    "ruinas", "acueducto", "dolmen", "dolmenes", "cueva", "cuevas",
    "fiesta", "fiestas", "romeria", "romerías", "festividad", "festividades",
    "tradicion", "tradiciones", "oficio", "oficios", "paisaje", "paisajes",
    "bien", "bienes", "inmueble", "inmuebles", "mueble", "muebles", "inmaterial",
}

_LOCATION_KEYWORDS = {
    "jaen", "jaén", "cordoba", "córdoba", "sevilla", "malaga", "málaga",
    "granada", "cadiz", "cádiz", "huelva", "almeria", "almería",
    "andalucia", "andalucía",
}

_STOPWORDS = {
    "de", "del", "la", "el", "los", "las", "un", "una", "en", "y", "a",
    "que", "qué", "es", "por", "con", "para", "al", "se", "lo", "como",
    "sobre", "hay", "me", "te", "nos", "les", "su", "mi", "tu",
    "dame", "dime", "hablame", "háblame", "cuentame", "cuéntame",
    "informacion", "información", "quiero", "saber", "necesito",
    "existen", "tiene", "tienen", "donde", "dónde", "cuales", "cuáles",
    "mas", "más", "otro", "otra", "otros", "otras", "ese", "esa",
    "esos", "esas", "cual", "cuál",
}


class QueryReformulator:
    """Reformulates follow-up queries by extracting entities from conversation history."""

    def reformulate(self, current: str, history: list[Message]) -> str:
        last_user_query = self._find_last_user_query(history)
        if not last_user_query:
            return current

        subject = self._extract_subject(last_user_query)
        new_location = self._extract_location(current)
        current_meaningful = self._extract_meaningful_terms(current)

        if new_location and subject:
            return f"{subject} en {new_location}"

        if subject and current_meaningful:
            return f"{subject} {current_meaningful}"

        if subject:
            return f"{subject} {current}"

        return current

    @staticmethod
    def _find_last_user_query(history: list[Message]) -> str | None:
        for msg in reversed(history):
            if msg.role == MessageRole.USER:
                return msg.content
        return None

    def _extract_subject(self, query: str) -> str:
        words = re.findall(r"\w+", query.lower())
        heritage = [w for w in words if w in _HERITAGE_KEYWORDS]
        return " ".join(heritage) if heritage else ""

    def _extract_location(self, text: str) -> str:
        words = re.findall(r"\w+", text.lower())
        locations = [w for w in words if w in _LOCATION_KEYWORDS]
        if locations:
            return locations[0].capitalize()
        return ""

    def _extract_meaningful_terms(self, text: str) -> str:
        words = re.findall(r"\w+", text.lower())
        meaningful = [
            w for w in words
            if w not in _STOPWORDS and w not in _LOCATION_KEYWORDS and len(w) > 1
        ]
        return " ".join(meaningful)
