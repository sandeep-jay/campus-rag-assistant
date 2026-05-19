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

from __future__ import annotations

import atexit
import contextlib
import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI  # noqa: TCH002

from backend.app.core.config_manager import settings
from backend.app.core.request_context import RequestIdFilter
from backend.app.utils.simple_tracer import get_client

VENDOR_LOGGER_LEVELS: dict[str, int] = {
    'boto3': logging.WARNING,
    'botocore': logging.WARNING,
    'urllib3': logging.WARNING,
    'httpcore': logging.WARNING,
    'sqlalchemy': logging.WARNING,
    'sqlalchemy.engine': logging.WARNING,
    'langsmith': logging.WARNING,
    'uvicorn.access': logging.INFO,
}

LOGGERS_TO_FOLLOW_APP = ('uvicorn', 'uvicorn.error', 'fastapi')

logger = logging.getLogger('app')

_logging_configured = False


class ThreadSafeHandler(logging.StreamHandler):
    """Suppress errors when stdout is closed during shutdown."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            super().emit(record)
        except ValueError as e:
            if 'I/O operation on closed file' in str(e):
                return
            raise


class JsonLogFormatter(logging.Formatter):
    """One JSON object per line for log aggregators."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            'ts': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'request_id': getattr(record, 'request_id', '-'),
            'pathname': record.pathname,
            'lineno': record.lineno,
        }
        if record.exc_info:
            payload['exc_info'] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _resolve_app_level() -> int:
    return getattr(logging, settings.LOGGING_LEVEL.upper(), logging.INFO)


def _vendor_levels(app_level: int) -> dict[str, int]:
    if app_level <= logging.DEBUG:
        return {name: app_level for name in VENDOR_LOGGER_LEVELS}
    return dict(VENDOR_LOGGER_LEVELS)


def _build_formatter(fmt: str) -> logging.Formatter:
    if settings.LOG_JSON:
        return JsonLogFormatter()
    return logging.Formatter(fmt)


def _attach_request_id_filter(handler: logging.Handler) -> None:
    handler.addFilter(RequestIdFilter())


def _create_console_handler(level: int, fmt: str) -> logging.Handler:
    handler = ThreadSafeHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(_build_formatter(fmt))
    _attach_request_id_filter(handler)
    return handler


def _create_file_handler(level: int, fmt: str) -> logging.Handler | None:
    if not settings.LOG_TO_FILE:
        return None
    try:
        log_path = Path(settings.LOGGING_LOCATION)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            filename=settings.LOGGING_LOCATION,
            maxBytes=10_485_760,
            backupCount=20,
            encoding='utf-8',
        )
        handler.setLevel(level)
        handler.setFormatter(_build_formatter(fmt))
        _attach_request_id_filter(handler)
        return handler
    except OSError as e:
        logging.getLogger('app.setup').error('Failed to create file handler: %s', e)
        return None


def _configure_vendor_loggers(app_level: int) -> None:
    levels = _vendor_levels(app_level)
    for name, level in levels.items():
        logging.getLogger(name).setLevel(level)
    for name in LOGGERS_TO_FOLLOW_APP:
        logging.getLogger(name).setLevel(app_level)


def initialize_logger(app: FastAPI | None = None) -> None:
    """Configure logging once per process (idempotent)."""
    global _logging_configured
    if _logging_configured:
        return

    app_level = _resolve_app_level()
    fmt = settings.LOGGING_FORMAT

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(app_level)

    logging.captureWarnings(True)

    console_handler = _create_console_handler(app_level, fmt)
    file_handler = _create_file_handler(app_level, fmt)
    root.addHandler(console_handler)
    if file_handler:
        root.addHandler(file_handler)

    logger.handlers.clear()
    logger.setLevel(app_level)
    logger.propagate = True

    _configure_vendor_loggers(app_level)

    if app is not None:
        fastapi_logger = logging.getLogger('fastapi')
        fastapi_logger.handlers.clear()
        fastapi_logger.propagate = True
        fastapi_logger.setLevel(app_level)

    _logging_configured = True
    logger.info('Logger initialized at level %s', logging.getLevelName(app_level))


def cleanup_logging() -> None:
    """Close handlers and LangSmith client on shutdown."""
    try:
        logging.getLogger('langsmith').setLevel(logging.CRITICAL)
        logging.getLogger('urllib3').setLevel(logging.CRITICAL)
        client = get_client()
        if client:
            with contextlib.suppress(Exception):
                client.session.close()
    except Exception:  # noqa: S110
        pass

    root = logging.getLogger()
    for handler in root.handlers[:]:
        with contextlib.suppress(Exception):
            handler.flush()
            handler.close()
            root.removeHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


atexit.register(cleanup_logging)
