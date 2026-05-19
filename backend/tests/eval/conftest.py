"""Pytest hooks for RAGAS eval (slow, cloud-backed)."""

import contextlib
import logging

import pytest

from backend.app.utils import simple_tracer


def _quiet_vendor_loggers() -> None:
    """Reduce httpx/openai/ragas noise during eval (RAGAS telemetry is opt-out via RAGAS_DO_NOT_TRACK)."""
    for name in (
        'httpx',
        'httpcore',
        'openai',
        'openai._base_client',
        'urllib3',
        'ragas',
        'ragas._analytics',
        'botocore',
        'boto3',
    ):
        logging.getLogger(name).setLevel(logging.WARNING)


def pytest_configure(config):
    _quiet_vendor_loggers()
    # Harmless urllib3 GeneratorExit when Bedrock streams close during pytest teardown
    config.addinivalue_line(
        'filterwarnings',
        'ignore:Exception ignored in.*read_chunked:pytest.PytestUnraisableExceptionWarning',
    )


@pytest.fixture(scope='session', autouse=True)
def _close_langsmith_client_after_eval():
    """Release LangSmith HTTP session so pytest shutdown is quiet."""
    yield
    with contextlib.suppress(Exception):
        if simple_tracer.client is not None:
            simple_tracer.client.close()
            simple_tracer.client = None
