import logging
import os
from logging.handlers import TimedRotatingFileHandler

from src.config import settings

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
USECASES_LOG_DIR = os.path.join(LOG_DIR, "usecases")
LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
BACKUP_COUNT = settings.log_retention_days

# ANSI color codes
_CYAN = "\033[36m"
_GREEN = "\033[32m"
_RESET = "\033[0m"

# Prefixes that mark user input lines (colored cyan)
_INPUT_PREFIXES = ("Processing message", "RAG pipeline start", "POST /")
# Prefixes that mark LLM output lines (colored green)
_OUTPUT_PREFIXES = ("Conversational LLM response", "RAG LLM response", "RAG pipeline complete")


class _ColorConsoleFormatter(logging.Formatter):
    """Console formatter that highlights user queries in cyan and LLM responses in green."""

    def format(self, record: logging.LogRecord) -> str:
        result = super().format(record)
        msg = record.getMessage()
        if any(msg.startswith(p) for p in _INPUT_PREFIXES):
            return f"{_CYAN}{result}{_RESET}"
        if any(msg.startswith(p) for p in _OUTPUT_PREFIXES):
            return f"{_GREEN}{result}{_RESET}"
        return result


class _ExcludeLoggerFilter(logging.Filter):
    """Exclude logs from a specific logger and its children."""

    def __init__(self, excluded: str) -> None:
        super().__init__()
        self._excluded = excluded

    def filter(self, record: logging.LogRecord) -> bool:
        return not record.name.startswith(self._excluded)


class _OnlyLoggerFilter(logging.Filter):
    """Allow only logs from a specific logger and its children."""

    def __init__(self, allowed: str) -> None:
        super().__init__()
        self._allowed = allowed

    def filter(self, record: logging.LogRecord) -> bool:
        return record.name.startswith(self._allowed)


class _MultiLoggerFilter(logging.Filter):
    """Allow logs from any of the listed loggers (prefix match)."""

    def __init__(self, allowed: list[str]) -> None:
        super().__init__()
        self._allowed = tuple(allowed)

    def filter(self, record: logging.LogRecord) -> bool:
        return any(record.name.startswith(a) for a in self._allowed)


def _daily_handler(
    filepath: str,
    level: int = logging.DEBUG,
    formatter: logging.Formatter | None = None,
    log_filter: logging.Filter | None = None,
) -> TimedRotatingFileHandler:
    """Create a TimedRotatingFileHandler that rotates daily at midnight,
    keeping BACKUP_COUNT days."""
    handler = TimedRotatingFileHandler(
        filepath, when="midnight", interval=1, backupCount=BACKUP_COUNT, utc=False,
    )
    handler.suffix = "%Y-%m-%d"
    handler.setLevel(level)
    if formatter:
        handler.setFormatter(formatter)
    if log_filter:
        handler.addFilter(log_filter)
    return handler


def setup_logging() -> None:
    """Configure the application logging system.

    Loggers:
        iaph            — general info, lifecycle, execution flow
        iaph.query      — API requests, search results, response summaries
        iaph.llm        — intent classification, LLM calls, RAG pipeline, responses
        iaph.embedding  — embedding service requests/responses
        iaph.auth       — login, token refresh, auth failures
        iaph.usecases.routes — route generation and guide queries
        iaph.usecases.search — similarity search queries

    File handlers (TimedRotatingFileHandler, daily rotation, 30 days):
        logs/info.log       ← iaph.* at INFO+
        logs/queries.log    ← iaph.query at DEBUG+
        logs/llm.log        ← iaph.llm at DEBUG+
        logs/embedding.log  ← iaph.embedding at DEBUG+
        logs/auth.log       ← iaph.auth at DEBUG+
        logs/feedback.log   ← iaph.feedback at DEBUG+
        logs/errors.log     ← root at WARNING+
        logs/usecases/routes.log  ← iaph.usecases.routes at DEBUG+
        logs/usecases/search.log  ← iaph.usecases.search at DEBUG+

    Console:
        iaph + iaph.llm + iaph.embedding + iaph.auth at INFO+ (excludes iaph.query)
    """
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(USECASES_LOG_DIR, exist_ok=True)
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # --- File handlers (daily rotation, 30-day retention) ---

    # info.log — all iaph.* logs at INFO+
    info_handler = _daily_handler(
        os.path.join(LOG_DIR, "info.log"), level=logging.INFO, formatter=formatter,
    )

    # queries.log — only iaph.query
    query_handler = _daily_handler(
        os.path.join(LOG_DIR, "queries.log"), formatter=formatter,
        log_filter=_OnlyLoggerFilter("iaph.query"),
    )

    # llm.log — only iaph.llm
    llm_handler = _daily_handler(
        os.path.join(LOG_DIR, "llm.log"), formatter=formatter,
        log_filter=_OnlyLoggerFilter("iaph.llm"),
    )

    # embedding.log — only iaph.embedding
    embedding_handler = _daily_handler(
        os.path.join(LOG_DIR, "embedding.log"), formatter=formatter,
        log_filter=_OnlyLoggerFilter("iaph.embedding"),
    )

    # auth.log — only iaph.auth
    auth_handler = _daily_handler(
        os.path.join(LOG_DIR, "auth.log"), formatter=formatter,
        log_filter=_OnlyLoggerFilter("iaph.auth"),
    )

    # feedback.log — only iaph.feedback
    feedback_handler = _daily_handler(
        os.path.join(LOG_DIR, "feedback.log"), formatter=formatter,
        log_filter=_OnlyLoggerFilter("iaph.feedback"),
    )

    # errors.log — WARNING+ from everything
    error_handler = _daily_handler(
        os.path.join(LOG_DIR, "errors.log"), level=logging.WARNING, formatter=formatter,
    )

    # usecases/routes.log — only iaph.usecases.routes
    routes_uc_handler = _daily_handler(
        os.path.join(USECASES_LOG_DIR, "routes.log"), formatter=formatter,
        log_filter=_OnlyLoggerFilter("iaph.usecases.routes"),
    )

    # usecases/search.log — only iaph.usecases.search
    search_uc_handler = _daily_handler(
        os.path.join(USECASES_LOG_DIR, "search.log"), formatter=formatter,
        log_filter=_OnlyLoggerFilter("iaph.usecases.search"),
    )

    # --- Console handler (info + llm + embedding + auth, NOT queries) ---
    color_formatter = _ColorConsoleFormatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(color_formatter)
    console_handler.addFilter(_ExcludeLoggerFilter("iaph.query"))

    # --- Configure loggers ---

    # iaph root logger — info.log + console + errors.log
    iaph_logger = logging.getLogger("iaph")
    iaph_logger.setLevel(logging.DEBUG)
    iaph_logger.addHandler(info_handler)
    iaph_logger.addHandler(console_handler)
    iaph_logger.addHandler(error_handler)
    iaph_logger.propagate = False

    # iaph.query — queries.log (inherits info.log + console from iaph parent)
    logging.getLogger("iaph.query").addHandler(query_handler)

    # iaph.llm — llm.log (inherits info.log + console from iaph parent)
    logging.getLogger("iaph.llm").addHandler(llm_handler)

    # iaph.embedding — embedding.log (inherits info.log + console from iaph parent)
    logging.getLogger("iaph.embedding").addHandler(embedding_handler)

    # iaph.auth — auth.log (inherits info.log + console from iaph parent)
    logging.getLogger("iaph.auth").addHandler(auth_handler)

    # iaph.feedback — feedback.log (inherits info.log + console from iaph parent)
    logging.getLogger("iaph.feedback").addHandler(feedback_handler)

    # iaph.usecases.routes — usecases/routes.log (inherits info.log + console from iaph parent)
    logging.getLogger("iaph.usecases.routes").addHandler(routes_uc_handler)

    # iaph.usecases.search — usecases/search.log (inherits info.log + console from iaph parent)
    logging.getLogger("iaph.usecases.search").addHandler(search_uc_handler)

    # Root logger — errors.log only (catches warnings from libraries)
    root = logging.getLogger()
    root.setLevel(logging.WARNING)
    root.addHandler(error_handler)

    # Silence noisy third-party loggers from console
    for name in (
        "sqlalchemy.engine",
        "uvicorn.access",
        "uvicorn.error",
        "uvicorn",
        "httpx",
        "httpcore",
        "watchfiles",
    ):
        lib_logger = logging.getLogger(name)
        lib_logger.setLevel(logging.WARNING)
        lib_logger.handlers.clear()
        lib_logger.propagate = True
