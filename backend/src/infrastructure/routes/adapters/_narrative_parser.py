"""Private helpers to parse LLM responses into :class:`RouteNarrative`.

Kept inside the infrastructure routes adapters package so the parsing
details (markdown stripping, regex fallbacks for truncated JSON) never
leak into the domain or the application layers.
"""

from __future__ import annotations

import json
import logging
import re

from src.application.shared.exceptions import LLMResponseParseError
from src.domain.routes.value_objects.route_narrative import RouteNarrative

logger = logging.getLogger("iaph.routes.llm")


def _strip_code_fences(raw: str) -> str:
    """Remove markdown code fences (```json ... ```) wrapping the response."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]  # remove opening ``` or ```json
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)
    return cleaned


def _strip_markdown(text: str) -> str:
    """Strip common markdown formatting from LLM output fields."""
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)  # **bold** -> bold
    text = re.sub(r"\*([^*]+)\*", r"\1", text)       # *italic* -> italic
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)  # ### heading -> heading
    text = re.sub(r"^---+$", "", text, flags=re.MULTILINE)  # --- separators
    return text.strip()


def _clean_title(title: str) -> str:
    """Strip markdown and remove common 'Titulo:' prefixes from title."""
    title = _strip_markdown(title)
    lower = title.lower()
    if lower.startswith("título:"):
        title = title[len("título:"):].strip()
    elif lower.startswith("titulo:"):
        title = title[len("titulo:"):].strip()
    return title


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

    cleaned = _strip_code_fences(raw)

    # Count expected stops from "order" occurrences (used for recovery logging).
    expected_stops = len(re.findall(r'"order"\s*:', cleaned))

    # 1. Strict JSON parse.
    try:
        data = json.loads(cleaned)
        title = _clean_title(
            data.get("title") or f"Ruta cultural por {province}",
        )
        introduction = _strip_markdown(data.get("introduction", "") or "")
        conclusion = _strip_markdown(data.get("conclusion", "") or "")
        segments: dict[int, str] = {}
        for stop in data.get("stops", []) or []:
            order = stop.get("order")
            narrative_text = stop.get("narrative", "")
            if order is not None and narrative_text:
                segments[int(order)] = _strip_markdown(narrative_text)
        return RouteNarrative(
            title=title,
            introduction=introduction,
            segments=segments,
            conclusion=conclusion,
            raw_response=raw,
            parse_method="json",
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

        title_match = re.search(
            r'"title"\s*:\s*"((?:[^"\\]|\\.)*)"', cleaned,
        )
        if title_match:
            title = title_match.group(1).replace('\\"', '"')

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

        # Extract complete narrative segments (escaped-quote aware).
        for stop_match in re.finditer(
            r'"order"\s*:\s*(\d+)\s*,\s*"narrative"\s*:\s*"((?:[^"\\]|\\.)*)"',
            cleaned,
        ):
            order = int(stop_match.group(1))
            narrative_text = stop_match.group(2).replace('\\"', '"')
            segments[order] = narrative_text

        # Try to capture a partial narrative if JSON was truncated mid-string.
        if expected_stops > len(segments):
            partial_match = re.search(
                r'"order"\s*:\s*(\d+)\s*,\s*"narrative"\s*:\s*"((?:[^"\\]|\\.)+)$',
                cleaned,
            )
            if partial_match:
                order = int(partial_match.group(1))
                if order not in segments:
                    partial_text = partial_match.group(2).replace('\\"', '"')
                    segments[order] = partial_text

        # Apply markdown stripping to all recovered fields.
        title = _clean_title(title)
        introduction = _strip_markdown(introduction)
        conclusion = _strip_markdown(conclusion)
        segments = {k: _strip_markdown(v) for k, v in segments.items()}

        if introduction or segments:
            logger.warning(
                "Recovered %d/%d narrative segments from truncated response",
                len(segments),
                expected_stops,
            )
            return RouteNarrative(
                title=title,
                introduction=introduction,
                segments=segments,
                conclusion=conclusion,
                raw_response=raw,
                parse_method="regex_fallback",
            )

    # 3. Plain-text fallback.
    logger.warning(
        "Failed to parse narrative JSON, using plain text fallback",
    )
    fallback_text = _strip_markdown(cleaned)
    return RouteNarrative(
        title=_extract_title_from_text(fallback_text, province),
        introduction=fallback_text,
        segments={},
        conclusion="",
        raw_response=raw,
        parse_method="plaintext_fallback",
    )
