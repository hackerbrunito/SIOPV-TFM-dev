"""Structured logging setup using structlog.

Configures JSON logging for production and colored console for development.
"""

import logging
import sys
from typing import Literal

import structlog


def configure_logging(
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO",
    json_format: bool = False,
    app_name: str = "SIOPV",
) -> None:
    """Configure structlog for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR).
        json_format: If True, output JSON. If False, colored console.
        app_name: Application name bound to every log event.
    """
    # Shared processors for both structlog and foreign (stdlib) loggers.
    # Note: filter_by_level is NOT included here because it requires a
    # bound logger with a 'disabled' attribute. Foreign loggers (e.g.,
    # Presidio running in thread pools) pass through foreign_pre_chain
    # with a raw stdlib LogRecord where the logger ref can be None,
    # causing AttributeError: 'NoneType' has no attribute 'disabled'.
    shared_processors: list[structlog.typing.Processor] = [
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        structlog.processors.CallsiteParameterAdder(
            {
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            }
        ),
    ]

    if json_format:
        # Production: ExceptionRenderer converts exc_info to string before JSONRenderer
        renderer: structlog.typing.Processor = structlog.processors.JSONRenderer()
        formatter_processors: list[structlog.typing.Processor] = [
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.ExceptionRenderer(),
            renderer,
        ]
    else:
        # Development: ConsoleRenderer handles exc_info natively (ExceptionRenderer not needed)
        renderer = structlog.dev.ConsoleRenderer(colors=True)
        formatter_processors = [
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ]

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Bind app_name globally so every log event carries it
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(app=app_name)

    # Configure stdlib logging
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=formatter_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, level))

    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("presidio_analyzer").setLevel(logging.WARNING)
    logging.getLogger("presidio_anonymizer").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a bound logger instance.

    Args:
        name: Logger name (typically __name__).

    Returns:
        Configured structlog bound logger.
    """
    # structlog.get_logger returns BoundLogger but typed as Any
    return structlog.get_logger(name)  # type: ignore[no-any-return]
