"""Structlog configuration for Setup Repository."""

import logging
from collections.abc import Generator
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars


def configure_logging(
    level: str = "INFO",
    log_file: Path | None = None,
) -> None:
    """Initialize logging configuration.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path for JSON Lines log file
    """
    # Shared processors
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
    ]

    if log_file:
        _setup_file_handler(log_file, shared_processors)

    # Console output configuration
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.ExceptionPrettyPrinter(),
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper())),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _setup_file_handler(
    log_file: Path,
    processors: list[structlog.types.Processor],
) -> None:
    """Set up JSON Lines file handler.

    Args:
        log_file: Path to the log file
        processors: List of structlog processors
    """
    log_file.parent.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        log_file,
        maxBytes=10_000_000,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=processors,
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Bound logger instance
    """
    return structlog.get_logger(name)


@contextmanager
def log_context(**kwargs: Any) -> Generator[None, None, None]:
    """Temporarily set log context variables.

    This is thread-safe using contextvars.

    Args:
        **kwargs: Context variables to bind

    Yields:
        None
    """
    bind_contextvars(**kwargs)
    try:
        yield
    finally:
        clear_contextvars()
