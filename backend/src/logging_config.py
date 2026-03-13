import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
MAX_BYTES = 10 * 1024 * 1024  # 10 MB per file
BACKUP_COUNT = 3


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


def setup_logging() -> None:
    """Configure the application logging system.

    Loggers:
        iaph        — general info, lifecycle, execution flow
        iaph.query  — API requests, search results, response summaries
        iaph.llm    — intent classification, LLM calls, RAG pipeline, responses

    File handlers (RotatingFileHandler):
        info.log    ← iaph.* at INFO+
        queries.log ← iaph.query at DEBUG+
        llm.log     ← iaph.llm at DEBUG+
        errors.log  ← root at WARNING+

    Console:
        iaph + iaph.llm at INFO+ (excludes iaph.query)
    """
    os.makedirs(LOG_DIR, exist_ok=True)
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # --- File handlers ---

    # info.log — all iaph.* logs at INFO+
    info_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "info.log"), maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT
    )
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)

    # queries.log — only iaph.query
    query_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "queries.log"), maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT
    )
    query_handler.setLevel(logging.DEBUG)
    query_handler.setFormatter(formatter)
    query_handler.addFilter(_OnlyLoggerFilter("iaph.query"))

    # llm.log — only iaph.llm
    llm_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "llm.log"), maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT
    )
    llm_handler.setLevel(logging.DEBUG)
    llm_handler.setFormatter(formatter)
    llm_handler.addFilter(_OnlyLoggerFilter("iaph.llm"))

    # errors.log — WARNING+ from everything
    error_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "errors.log"), maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(formatter)

    # --- Console handler (info + llm, NOT queries) ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
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

    # Root logger — errors.log only (catches warnings from libraries)
    root = logging.getLogger()
    root.setLevel(logging.WARNING)
    root.addHandler(error_handler)
