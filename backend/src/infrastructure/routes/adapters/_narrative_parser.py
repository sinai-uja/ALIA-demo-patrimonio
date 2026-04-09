"""Private helpers to parse LLM responses into :class:`RouteNarrative`.

Kept inside the infrastructure routes adapters package so the parsing
details (markdown stripping, regex fallbacks for truncated JSON) never
leak into the domain or the application layers.
"""

from __future__ import annotations

import json
import logging
import re

from src.domain.routes.value_objects.route_narrative import RouteNarrative
from src.infrastructure.shared.exceptions import LLMResponseParseError

logger = logging.getLogger("iaph.llm")


def _strip_markdown(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]  # remove opening ``` or ```json
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)
    return cleaned


def _extract_title_from_text(narrative: str, province: str) -> str:
    if narrative:
        stripped = narrative.strip()
        if stripped.startswith("{"):
            title_match = re.search(r'"title"\s*:\s*"([^"]+)"', stripped)
            if title_match:
                return title_match.group(1)
            return f"Ruta cultural por {province}"
        first_line = stripped.split("\n")[0].strip()
        clean = (
            first_line.lstrip("#")
            .strip()
            .strip('"')
            .strip("*")
            .strip()
        )
        if clean and len(clean) < 200:
            return clean
    return f"Ruta cultural por {province}"


def parse_narrative_json(raw: str, province: str) -> RouteNarrative:
    """Parse a raw LLM response into a :class:`RouteNarrative`.

    Attempts, in order:

    1. Strict JSON parsing after stripping markdown fences.
    2. Regex extraction of individual fields for truncated JSON.
    3. Plain-text fallback (title extracted heuristically, the full
       response used as the introduction).

    Raises:
        LLMResponseParseError: If the response is not a string at all.
    """
    if not isinstance(raw, str):
        raise LLMResponseParseError(
            f"Expected str LLM response, got {type(raw).__name__}",
        )

    cleaned = _strip_markdown(raw)

    # 1. Strict JSON parse.
    try:
        data = json.loads(cleaned)
        title = data.get("title") or f"Ruta cultural por {province}"
        introduction = data.get("introduction", "") or ""
        conclusion = data.get("conclusion", "") or ""
        segments: dict[int, str] = {}
        for stop in data.get("stops", []) or []:
            order = stop.get("order")
            narrative_text = stop.get("narrative", "")
            if order is not None and narrative_text:
                segments[int(order)] = narrative_text
        return RouteNarrative(
            title=title,
            introduction=introduction,
            segments=segments,
            conclusion=conclusion,
        )
    except (json.JSONDecodeError, AttributeError, TypeError):
        pass

    # 2. Regex fallback for truncated JSON.
    if cleaned.startswith("{"):
        logger.warning(
            "Full JSON parse failed, attempting regex extraction "
            "from truncated response (%d chars)",
            len(cleaned),
        )
        title = f"Ruta cultural por {province}"
        introduction = ""
        conclusion = ""
        segments = {}

        title_match = re.search(r'"title"\s*:\s*"([^"]+)"', cleaned)
        if title_match:
            title = title_match.group(1)

        intro_match = re.search(
            r'"introduction"\s*:\s*"((?:[^"\\]|\\.)*)"', cleaned,
        )
        if intro_match:
            introduction = intro_match.group(1).replace('\\"', '"')

        conclusion_match = re.search(
            r'"conclusion"\s*:\s*"((?:[^"\\]|\\.)*)"', cleaned,
        )
        if conclusion_match:
            conclusion = conclusion_match.group(1).replace('\\"', '"')

        for stop_match in re.finditer(
            r'"order"\s*:\s*(\d+)\s*,\s*"narrative"\s*:\s*"((?:[^"\\]|\\.)*)"',
            cleaned,
        ):
            order = int(stop_match.group(1))
            narrative_text = stop_match.group(2).replace('\\"', '"')
            segments[order] = narrative_text

        if introduction or segments:
            logger.info(
                "Regex extraction recovered: title=%s, intro=%d chars, "
                "%d stop segments, conclusion=%d chars",
                title[:50],
                len(introduction),
                len(segments),
                len(conclusion),
            )
            return RouteNarrative(
                title=title,
                introduction=introduction,
                segments=segments,
                conclusion=conclusion,
            )

    # 3. Plain-text fallback.
    logger.warning(
        "Failed to parse narrative JSON, using plain text fallback",
    )
    return RouteNarrative(
        title=_extract_title_from_text(cleaned, province),
        introduction=cleaned,
        segments={},
        conclusion="",
    )
