"""
Copyright ©2025. The Regents of the University of California (Regents). All Rights Reserved.

Permission to use, copy, modify, and distribute this software and its documentation
for educational, research, and not-for-profit purposes, without fee and without a
signed licensing agreement, is hereby granted, provided that the above copyright
notice, this paragraph and the following two paragraphs appear in all copies,
modifications, and distributions.

Contact The Office of Technology Licensing, UC Berkeley, 2150 Shattuck Avenue,
Suite 510, Berkeley, CA 94720-1620, (510) 643-7201, otl@berkeley.edu,
http://ipira.berkeley.edu/industry-info for commercial licensing opportunities.

IN NO EVENT SHALL REGENTS BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT, SPECIAL,
INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING OUT OF
THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF REGENTS HAS BEEN ADVISED
OF THE POSSIBILITY OF SUCH DAMAGE.

REGENTS SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE
SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, PROVIDED HEREUNDER IS PROVIDED
"AS IS". REGENTS HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES,
ENHANCEMENTS, OR MODIFICATIONS.
"""

import atexit
import contextlib
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI

from backend.app.core.config_manager import settings
from backend.app.utils.simple_tracer import get_client

"""Logging configuration for the backend application."""

# Define loggers to be configured
LOGGERS_TO_CONFIGURE = [
    'uvicorn',
    'uvicorn.error',
    'uvicorn.access',
    'fastapi',
    'boto3',
    'botocore',
    'sqlalchemy',
    # 'langsmith' is handled separately with a custom handler
]

# Create the logger instance that will be exported
logger = logging.getLogger('app')


class ThreadSafeHandler(logging.StreamHandler):
    """A thread-safe handler that suppresses errors on closed streams during shutdown."""

    def emit(self, record):
        # Emit a record handling closed file errors during shutdown.
        try:
            super().emit(record)
        except ValueError as e:
            # Check if this is a closed file error during shutdown
            if 'I/O operation on closed file' in str(e):
                # Silently ignore I/O errors on closed files
                return
            # Re-raise other ValueErrors
            raise


def _create_console_handler(level: int, fmt: str) -> logging.Handler:
    # Create a console handler for logging.
    handler = ThreadSafeHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(fmt))
    return handler


def _create_file_handler(level: int, fmt: str) -> logging.Handler | None:
    # Create a file handler for logging if enabled in settings.
    if not settings.LOG_TO_FILE:
        return None
    try:
        log_path = Path(settings.LOGGING_LOCATION)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            filename=settings.LOGGING_LOCATION,
            maxBytes=10_485_760,  # 10MB
            backupCount=20,
            encoding='utf-8',
        )
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter(fmt))
        logger.info(f'File logging enabled at {settings.LOGGING_LOCATION}')
        return handler
    except Exception as e:
        logger.error(f'Failed to create file handler: {e}')
        return None


def _configure_langsmith_logger(level: int) -> None:
    # Configure the LangSmith logger with thread-safe handlers.
    langsmith_logger = logging.getLogger('langsmith')
    langsmith_logger.handlers.clear()
    langsmith_logger.setLevel(level)

    # Use thread-safe handler for LangSmith
    handler = ThreadSafeHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(settings.LOGGING_FORMAT))
    langsmith_logger.addHandler(handler)

    # Also configure urllib3 logger which is used by LangSmith
    urllib3_logger = logging.getLogger('urllib3')
    urllib3_logger.handlers.clear()
    urllib3_logger.addHandler(handler)


def initialize_logger(app: FastAPI | None = None) -> None:
    # Initialize and configure backend logging.

    level = getattr(logging, settings.LOGGING_LEVEL.upper(), logging.INFO)
    fmt = settings.LOGGING_FORMAT

    # Clear and configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)

    # Capture warnings
    logging.captureWarnings(True)

    # Handlers
    console_handler = _create_console_handler(level, fmt)
    file_handler = _create_file_handler(level, fmt)

    root_logger.addHandler(console_handler)
    if file_handler:
        root_logger.addHandler(file_handler)

    # Configure app logger
    logger.handlers.clear()
    logger.setLevel(level)
    logger.addHandler(console_handler)
    if file_handler:
        logger.addHandler(file_handler)

    # Configure third-party loggers
    for logger_name in LOGGERS_TO_CONFIGURE:
        logging.getLogger(logger_name).setLevel(level)

    # Special configuration for LangSmith logger
    _configure_langsmith_logger(level)

    # Optionally configure FastAPI logger
    if app:
        fastapi_logger = logging.getLogger('fastapi')
        fastapi_logger.handlers.clear()
        fastapi_logger.setLevel(level)
        fastapi_logger.addHandler(console_handler)
        if file_handler:
            fastapi_logger.addHandler(file_handler)

    logger.info(f'Logger initialized at level {logging.getLevelName(level)}')


def cleanup_logging() -> None:
    """Close all handlers and cleanup LangSmith."""
    # First cleanup LangSmith client if it exists
    try:
        # Disable langsmith logger to prevent logging after handlers are closed
        logging.getLogger('langsmith').setLevel(logging.CRITICAL)
        logging.getLogger('urllib3').setLevel(logging.CRITICAL)

        client = get_client()
        if client:
            with contextlib.suppress(Exception):
                client.session.close()
    except Exception:  # noqa: S110
        # Silent exception handling is intentional here
        # We're in cleanup code and can't log errors as handlers may be closed
        pass

    # Close all handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        with contextlib.suppress(Exception):
            handler.flush()
            handler.close()
            root_logger.removeHandler(handler)


def get_logger(name: str) -> logging.Logger:
    # Get a configured logger.

    return logging.getLogger(name)


# Register cleanup function to ensure proper resource release
atexit.register(cleanup_logging)

# Initialize logging when module is imported
initialize_logger()
