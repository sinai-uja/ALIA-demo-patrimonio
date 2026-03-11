SYSTEM_PROMPT = (
    "Eres un experto en patrimonio historico andaluz del Instituto Andaluz de Patrimonio "
    "Historico (IAPH).\n"
    "Responde en espanol de forma clara y precisa basandote unicamente en el contexto "
    "proporcionado.\n"
    "Si la informacion no esta en el contexto, indicalo explicitamente."
)


def build_user_prompt(query: str, context: str) -> str:
    return (
        f"Contexto del patrimonio historico:\n\n{context}\n\n"
        f"Pregunta: {query}\n\n"
        f"Respuesta:"
    )
