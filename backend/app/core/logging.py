"""Structured logging configuration for Flowex.

Provides JSON-structured logging for production (CloudWatch-compatible)
and human-readable logging for development.
"""

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# Context variable for request correlation ID
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class JSONFormatter(logging.Formatter):
    """JSON log formatter for CloudWatch and log aggregation systems."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add request correlation ID if available
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id

        # Add extra fields from record
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add source location
        log_data["source"] = {
            "file": record.pathname,
            "line": record.lineno,
            "function": record.funcName,
        }

        return json.dumps(log_data, default=str)


class DevelopmentFormatter(logging.Formatter):
    """Human-readable log formatter for development."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[41m",  # Red background
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors and request ID."""
        # Add color for level
        color = self.COLORS.get(record.levelname, "")
        reset = self.RESET if color else ""

        # Build the message
        request_id = request_id_var.get()
        rid_part = f"[{request_id[:8]}] " if request_id else ""

        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        message = f"{timestamp} {color}{record.levelname:8}{reset} {rid_part}{record.name}: {record.getMessage()}"

        # Add exception info if present
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)

        return message


def setup_logging(debug: bool = False, json_logs: bool = False) -> None:
    """Configure application logging.

    Args:
        debug: If True, set log level to DEBUG. Otherwise INFO.
        json_logs: If True, use JSON formatting. Otherwise use development formatter.
    """
    # Determine log level
    log_level = logging.DEBUG if debug else logging.INFO

    # Create handler
    handler = logging.StreamHandler(sys.stdout)

    # Select formatter based on environment
    if json_logs:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(DevelopmentFormatter())

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.

    Args:
        name: Logger name, typically __name__.

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)


def generate_request_id() -> str:
    """Generate a unique request ID.

    Returns:
        UUID string for request correlation.
    """
    return str(uuid.uuid4())


def set_request_id(request_id: str) -> None:
    """Set the request ID for the current context.

    Args:
        request_id: The request ID to set.
    """
    request_id_var.set(request_id)


def get_request_id() -> str:
    """Get the request ID for the current context.

    Returns:
        The current request ID or empty string.
    """
    return request_id_var.get()
