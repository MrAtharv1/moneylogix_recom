"""
logger.py — Structured logging configuration for MoneyLogix Strategy Builder.

Sets up JSON-structured logging so that log output is machine-parseable
in production (e.g., by Datadog, CloudWatch, or a log aggregator) while
remaining human-readable in development.

Usage (in any module):
    from utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Strategy analyzed", extra={"symbol": "NIFTY", "legs": 4})

Design decisions:
  - One call to setup_logging() in main.py startup configures the root logger.
  - All other modules call get_logger(__name__) — the spec's prescribed pattern.
  - In development (LOG_FORMAT=text), output is coloured and human-readable.
  - In production (LOG_FORMAT=json), output is one JSON object per line.
  - Log level is controlled by LOG_LEVEL in .env (default: INFO).
"""

import logging
import json
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON objects.

    Each log line is a complete JSON object. The "module" key matches the
    spec's prescribed shape. Any extras passed via the `extra` kwarg in
    logger.info() / logger.error() are included as top-level fields.

    Example output:
    {"timestamp": "2024-01-15T10:23:45.123Z", "level": "INFO",
     "module": "ai.claude_provider", "message": "Claude API failed",
     "symbol": "NIFTY", "response_time_ms": 245}
    """

    def format(self, record: logging.LogRecord) -> str:
        # Base fields — matches spec's prescribed JSON shape
        log_obj = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level":   record.levelname,
            "module":  record.name,       # "module" key per spec
            "message": record.getMessage(),
        }

        # Include exception traceback if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Include any extra fields passed via extra={} kwarg.
        # We skip standard LogRecord attributes that are internal bookkeeping.
        _SKIP = {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "message",
            "taskName",
        }
        for key, value in record.__dict__.items():
            if key not in _SKIP:
                log_obj[key] = value

        return json.dumps(log_obj, default=str)


class HumanFormatter(logging.Formatter):
    """
    Human-readable coloured formatter for development.

    Example output:
    2024-01-15 10:23:45 | INFO     | ai.claude_provider            | Claude API failed
    """

    LEVEL_COLORS = {
        "DEBUG":    "\033[36m",   # Cyan
        "INFO":     "\033[32m",   # Green
        "WARNING":  "\033[33m",   # Yellow
        "ERROR":    "\033[31m",   # Red
        "CRITICAL": "\033[35m",   # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color     = self.LEVEL_COLORS.get(record.levelname, "")
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        level     = f"{color}{record.levelname:<8}{self.RESET}"
        return f"{timestamp} | {level} | {record.name:<30} | {record.getMessage()}"


def setup_logging(level: str = "INFO", log_format: str = "text") -> None:
    """
    Configure the root logger. Call once from main.py startup.

    Signature matches spec: primary arg is `level` (not `log_level`).

    Args:
        level      : "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
        log_format : "text" for human-readable dev output (default),
                     "json" for structured production output
    """
    formatter = JSONFormatter() if log_format == "json" else HumanFormatter()

    # Stream to stdout — captured by container log drivers in production
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Configure root logger — all child loggers (every module) inherit this
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    root_logger.handlers.clear()   # Prevents duplicate handlers on uvicorn --reload
    root_logger.addHandler(handler)

    # Quieten noisy third-party loggers that spam DEBUG at INFO level
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    get_logger(__name__).info(
        f"Logging configured: level={level}, format={log_format}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Returns a named logger. Use in every module:

        from utils.logger import get_logger
        logger = get_logger(__name__)

    This is a thin wrapper around logging.getLogger() — the value-add is that
    it documents the prescribed import pattern and makes it greppable
    across the codebase.
    """
    return logging.getLogger(name)