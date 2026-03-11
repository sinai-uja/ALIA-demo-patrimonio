ROUTE_SYSTEM_PROMPT = """Eres un experto guia turistico del patrimonio historico andaluz del IAPH.
Genera rutas culturales personalizadas en espanol, detalladas y atractivas para el visitante."""


def build_route_prompt(
    province: str,
    num_stops: int,
    heritage_types: list[str],
    context: str,
) -> str:
    return f"""Crea una ruta cultural por {province} con {num_stops} paradas.
Tipos de patrimonio: {', '.join(heritage_types)}.

Contexto del patrimonio disponible:
{context}

Genera un titulo atractivo para la ruta y una narrativa introductoria de 3-4 parrafos \
que conecte los elementos patrimoniales."""


GUIDE_SYSTEM_PROMPT = """Eres un guia experto del patrimonio historico andaluz.
Responde preguntas sobre la ruta y los elementos patrimoniales \
en espanol, de forma cercana y detallada."""


def build_guide_prompt(question: str, route_context: str, rag_context: str) -> str:
    return (
        f"Contexto de la ruta:\n{route_context}\n\n"
        f"Informacion adicional del patrimonio:\n{rag_context}\n\n"
        f"Pregunta del visitante: {question}\n\n"
        f"Respuesta:"
    )
