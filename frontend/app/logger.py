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

from app.config import settings

"""Logging configuration for the frontend application."""

# Define loggers to be configured
LOGGERS_TO_CONFIGURE = [
    'boto3',
    'streamlit',
    'PIL',
]

# Create the logger instance that will be exported
logger = logging.getLogger('app')


def _create_console_handler(level: int, fmt: str) -> logging.Handler:
    # Create a console handler for logging.
    handler = logging.StreamHandler(sys.stdout)
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
            maxBytes=1024 * 1024 * 100,  # 100MB
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


def initialize_logger() -> None:
    # Initialize logging configuration.
    level = getattr(logging, settings.LOGGING_LEVEL.upper(), logging.INFO)
    fmt = settings.LOGGING_FORMAT

    # Configure root logger to capture warnings
    logging.captureWarnings(True)

    # Clear and configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)

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
    external_level = getattr(
        logging,
        settings.LOGGING_PROPAGATION_LEVEL.upper(),
        logging.INFO,
    )
    for logger_name in LOGGERS_TO_CONFIGURE:
        logging.getLogger(logger_name).setLevel(external_level)

    logger.info(f'Logger initialized with level {settings.LOGGING_LEVEL}')


def cleanup_logging() -> None:
    # Close all logging handlers before shutdown.
    # Close all handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        with contextlib.suppress(Exception):
            handler.flush()
            handler.close()
            root_logger.removeHandler(handler)


def get_logger(name: str) -> logging.Logger:
    # Get a logger instance with the specified name.
    return logging.getLogger(name)


# Register cleanup function to ensure proper resource release
atexit.register(cleanup_logging)
