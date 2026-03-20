QUERY_EXTRACTION_SYSTEM_PROMPT = (
    "Eres un asistente experto en patrimonio historico andaluz del IAPH. "
    "A partir del texto del usuario, extrae una consulta de busqueda "
    "concisa (maximo 10 palabras) para recuperar bienes patrimoniales.\n\n"
    "Reglas ESTRICTAS:\n"
    "- SIMPLIFICA la consulta, NUNCA anadas palabras que el usuario no "
    "haya escrito.\n"
    "- NO inventes ni anadas tipos patrimoniales (etnologico, inmueble, "
    "mueble, etc.) si el usuario no los menciono.\n"
    "- NO anadas ubicaciones si el usuario no las menciono.\n"
    "- Si la consulta del usuario ya es clara y corta, devuelvela TAL CUAL.\n"
    "- Responde SOLO con la consulta, sin explicaciones ni formato adicional."
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
    "y atractivas.\n\n"
    "Responde UNICAMENTE con un objeto JSON valido (sin bloques de codigo "
    "ni markdown) con esta estructura exacta:\n"
    "{\n"
    '  "title": "Titulo atractivo de la ruta (sin comillas extras ni markdown)",\n'
    '  "introduction": "Parrafo introductorio (3-4 frases) presentando el tema",\n'
    '  "stops": [\n'
    '    {"order": 1, "narrative": "Parrafo narrativo sobre esta parada, '
    "su historia y conexion con la siguiente\"},\n"
    '    {"order": 2, "narrative": "..."}\n'
    "  ],\n"
    '  "conclusion": "Parrafo de cierre que resuma el recorrido"\n'
    "}\n\n"
    "Reglas:\n"
    "- Genera EXACTAMENTE un elemento en stops por cada parada listada\n"
    "- Cada narrative debe describir el bien patrimonial concreto de esa "
    "parada y crear una transicion natural hacia la siguiente\n"
    "- Usa SOLO la informacion proporcionada en el contexto\n"
    "- No inventes datos ni lugares que no aparezcan en el contexto"
)


def build_route_prompt(
    query: str,
    stops_context: str,
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
        f"Genera una narrativa para una ruta cultural con las "
        f"siguientes paradas.\n"
        f"{location_line}"
        f"Tema de busqueda del visitante: {query}\n\n"
        f"Paradas de la ruta (en orden):\n{stops_context}\n\n"
        f"Genera el JSON con title, introduction, un narrative por "
        f"cada parada y conclusion."
    )


GUIDE_SYSTEM_PROMPT = (
    "Eres un guia experto del patrimonio historico andaluz del IAPH. "
    "Respondes preguntas sobre una ruta cultural concreta y sus paradas "
    "en espanol, de forma cercana, detallada y precisa.\n\n"
    "Reglas:\n"
    "- Responde UNICAMENTE con la informacion de las paradas de la ruta "
    "proporcionada. No inventes datos.\n"
    "- Si la pregunta trata sobre algo que NO esta en las paradas de la "
    "ruta, indica amablemente que esa informacion no forma parte de esta "
    "ruta y sugiere al visitante usar la herramienta de busqueda o crear "
    "una nueva ruta en la web.\n"
    "- Cita las paradas por su nombre cuando sea relevante.\n"
    "- Se descriptivo y ameno, como un guia turistico profesional."
)


def build_guide_prompt(
    question: str, route_context: str,
) -> str:
    return (
        f"Informacion detallada de las paradas de la ruta:\n\n"
        f"{route_context}\n\n"
        f"Pregunta del visitante: {question}\n\n"
        f"Respuesta:"
    )
