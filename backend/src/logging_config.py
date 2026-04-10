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
_OUTPUT_PREFIXES = ("LLM response:", "RAG pipeline complete", "Gemini")


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

    Namespaces follow `iaph.<bounded_context>.<concept>`:
        iaph                  — general info, lifecycle, execution flow
        iaph.rag.*            — RAG pipeline (query, llm, reranker, embedding,
                                text_search, vector_search, router)
        iaph.chat.*           — chat bounded context (intent, reformulator,
                                llm, router, send_message)
        iaph.routes.*         — routes bounded context (generate_route, llm,
                                heritage_lookup, router)
        iaph.search.*         — similarity search bounded context
        iaph.documents.*      — documents ingestion (embedding, ingest)
        iaph.accessibility.*  — accessibility bounded context (llm)
        iaph.auth             — login, token refresh, auth failures
        iaph.feedback         — feedback submissions
        iaph.api.exceptions   — global HTTP exception translation
        iaph.infra.*          — generic infra-layer diagnostics

    File handlers (TimedRotatingFileHandler, daily rotation, 30 days):
        logs/info.log       ← iaph.* at INFO+
        logs/queries.log    ← iaph.rag.* + iaph.chat.intent/reformulator/router
        logs/llm.log        ← every iaph.<ctx>.llm adapter
        logs/embedding.log  ← iaph.shared.embedding
        logs/auth.log       ← iaph.auth at DEBUG+
        logs/feedback.log   ← iaph.feedback at DEBUG+
        logs/errors.log     ← root at WARNING+
        logs/usecases/routes.log  ← iaph.routes.*
        logs/usecases/search.log  ← iaph.search.*

    Console:
        iaph.* at INFO+ (all loggers)
    """
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(USECASES_LOG_DIR, exist_ok=True)
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # --- File handlers (daily rotation, 30-day retention) ---

    # info.log — all iaph.* logs at INFO+
    info_handler = _daily_handler(
        os.path.join(LOG_DIR, "info.log"), level=logging.INFO, formatter=formatter,
    )

    # queries.log — RAG pipeline + chat intent/reformulator
    query_handler = _daily_handler(
        os.path.join(LOG_DIR, "queries.log"), formatter=formatter,
        log_filter=_MultiLoggerFilter([
            "iaph.rag",
            "iaph.chat.intent",
            "iaph.chat.reformulator",
            "iaph.chat.router",
        ]),
    )

    # llm.log — all LLM adapters regardless of bounded context
    llm_handler = _daily_handler(
        os.path.join(LOG_DIR, "llm.log"), formatter=formatter,
        log_filter=_MultiLoggerFilter([
            "iaph.rag.llm",
            "iaph.chat.llm",
            "iaph.routes.llm",
            "iaph.accessibility.llm",
        ]),
    )

    # embedding.log — embedding adapters in any bounded context
    embedding_handler = _daily_handler(
        os.path.join(LOG_DIR, "embedding.log"), formatter=formatter,
        log_filter=_MultiLoggerFilter([
            "iaph.shared.embedding",
        ]),
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

    # usecases/routes.log — everything in the routes bounded context
    routes_uc_handler = _daily_handler(
        os.path.join(USECASES_LOG_DIR, "routes.log"), formatter=formatter,
        log_filter=_OnlyLoggerFilter("iaph.routes"),
    )

    # usecases/search.log — everything in the search bounded context
    search_uc_handler = _daily_handler(
        os.path.join(USECASES_LOG_DIR, "search.log"), formatter=formatter,
        log_filter=_OnlyLoggerFilter("iaph.search"),
    )

    # --- Console handler (all iaph.* loggers at INFO+) ---
    color_formatter = _ColorConsoleFormatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(color_formatter)
    # iaph.query logs now include RAG pipeline messages — show them in console

    # --- Configure loggers ---

    # iaph root logger — info.log + console + errors.log
    iaph_logger = logging.getLogger("iaph")
    iaph_logger.setLevel(logging.DEBUG)
    iaph_logger.addHandler(info_handler)
    iaph_logger.addHandler(console_handler)
    iaph_logger.addHandler(error_handler)
    iaph_logger.propagate = False

    # queries.log — attach to the iaph parent, the filter scopes which
    # namespaces are actually written (RAG + chat intent/reformulator).
    iaph_logger.addHandler(query_handler)

    # llm.log — attach to iaph parent; filter scopes to per-context LLM loggers.
    iaph_logger.addHandler(llm_handler)

    # embedding.log — attach to iaph parent; filter scopes to embedding adapters.
    iaph_logger.addHandler(embedding_handler)

    # iaph.auth — auth.log (inherits info.log + console from iaph parent)
    logging.getLogger("iaph.auth").addHandler(auth_handler)

    # iaph.feedback — feedback.log (inherits info.log + console from iaph parent)
    logging.getLogger("iaph.feedback").addHandler(feedback_handler)

    # iaph.routes — usecases/routes.log (whole routes bounded context)
    logging.getLogger("iaph.routes").addHandler(routes_uc_handler)

    # iaph.search — usecases/search.log (whole search bounded context)
    logging.getLogger("iaph.search").addHandler(search_uc_handler)

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
