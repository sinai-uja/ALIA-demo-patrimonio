QUERY_EXTRACTION_SYSTEM_PROMPT = (
    "Eres un asistente experto en patrimonio historico andaluz del IAPH. "
    "A partir del texto del usuario, extrae una consulta de busqueda "
    "concisa (maximo 10-15 palabras) para recuperar bienes patrimoniales "
    "relevantes. La consulta debe capturar la esencia de lo que el "
    "usuario quiere visitar. Responde SOLO con la consulta, sin "
    "explicaciones ni formato adicional."
)


def build_query_extraction_prompt(
    cleaned_text: str,
    province_filter: list[str] | None = None,
    municipality_filter: list[str] | None = None,
) -> str:
    filter_lines = []
    if province_filter:
        filter_lines.append(
            f"- Provincia: {', '.join(province_filter)}",
        )
    if municipality_filter:
        filter_lines.append(
            f"- Municipio: {', '.join(municipality_filter)}",
        )
    filters_block = (
        "\n".join(filter_lines) if filter_lines else "- Ninguno"
    )
    location_note = (
        "La ubicacion YA esta en los filtros, NO la incluyas en la "
        "consulta."
        if province_filter or municipality_filter
        else "No hay filtro de ubicacion. Incluye la ubicacion en la "
        "consulta si el usuario la menciona."
    )
    return (
        f"Texto del usuario: {cleaned_text}\n\n"
        f"Filtros activos (ya aplicados en la busqueda):\n"
        f"{filters_block}\n\n"
        f"{location_note}\n\n"
        f"Consulta de busqueda:"
    )


ROUTE_SYSTEM_PROMPT = (
    "Eres un experto guia turistico del patrimonio historico andaluz del "
    "IAPH. Genera narrativas de rutas culturales en espanol, detalladas "
    "y atractivas. Estructura tu respuesta asi:\n"
    "1. Un titulo atractivo en la primera linea (sin formato markdown, "
    "sin comillas)\n"
    "2. Un parrafo introductorio (3-4 frases) presentando el tema de la "
    "ruta\n"
    "3. Para cada parada, un breve parrafo narrativo que cuente su "
    "historia y conecte con la siguiente parada\n"
    "Usa SOLO la informacion proporcionada en el contexto. "
    "No inventes datos ni lugares que no aparezcan en el contexto."
)


def build_route_prompt(
    query: str,
    num_stops: int,
    context: str,
    province: list[str] | None = None,
    municipality: list[str] | None = None,
) -> str:
    location_parts = []
    if province:
        location_parts.append(
            f"Provincia: {', '.join(province)}",
        )
    if municipality:
        location_parts.append(
            f"Municipio: {', '.join(municipality)}",
        )
    location_line = (
        f"Ubicacion: {'; '.join(location_parts)}\n"
        if location_parts
        else ""
    )
    return (
        f"Genera una ruta cultural con {num_stops} paradas.\n"
        f"{location_line}"
        f"Tema de busqueda del visitante: {query}\n\n"
        f"Patrimonio disponible:\n{context}\n\n"
        f"Escribe un titulo, una introduccion y una narrativa que "
        f"conecte las paradas contando la historia del patrimonio "
        f"visitado."
    )


GUIDE_SYSTEM_PROMPT = """Eres un guia experto del patrimonio historico andaluz.
Responde preguntas sobre la ruta y los elementos patrimoniales \
en espanol, de forma cercana y detallada."""


def build_guide_prompt(
    question: str, route_context: str, rag_context: str,
) -> str:
    return (
        f"Contexto de la ruta:\n{route_context}\n\n"
        f"Informacion adicional del patrimonio:\n{rag_context}\n\n"
        f"Pregunta del visitante: {question}\n\n"
        f"Respuesta:"
    )
