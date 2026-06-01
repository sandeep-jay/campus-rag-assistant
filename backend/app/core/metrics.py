from __future__ import annotations

import time
from contextlib import contextmanager, suppress
from typing import TYPE_CHECKING

from fastapi import Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

REQUEST_COUNT = Counter(
    'chatbot_http_requests_total',
    'Total HTTP requests',
    ['method', 'path', 'status_code'],
)
REQUEST_LATENCY_SECONDS = Histogram(
    'chatbot_http_request_latency_seconds',
    'HTTP request latency by route',
    ['method', 'path'],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)
REQUEST_EXCEPTIONS = Counter(
    'chatbot_http_request_exceptions_total',
    'Unhandled request exceptions',
    ['method', 'path'],
)
PROVIDER_LATENCY_SECONDS = Histogram(
    'chatbot_provider_latency_seconds',
    'Latency of provider calls',
    ['provider', 'operation', 'outcome'],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 20),
)
PROVIDER_ERRORS = Counter(
    'chatbot_provider_errors_total',
    'Provider call failures by reason',
    ['provider', 'operation', 'reason'],
)
DB_POOL_SIZE = Gauge('chatbot_db_pool_size', 'Configured DB pool size')
DB_POOL_CHECKED_OUT = Gauge('chatbot_db_pool_checked_out', 'Checked out DB connections')
DB_POOL_CHECKED_IN = Gauge('chatbot_db_pool_checked_in', 'Checked in DB connections')
DB_POOL_OVERFLOW = Gauge('chatbot_db_pool_overflow', 'DB pool overflow connections')
DB_POOL_USAGE_RATIO = Gauge('chatbot_db_pool_usage_ratio', 'Checked out / max DB connections')
CHAT_FIRST_TOKEN_LATENCY_SECONDS = Histogram(
    'chatbot_chat_first_token_latency_seconds',
    'Time from SSE stream open to first token event',
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60),
)

HELPDESK_RECAP_TOTAL = Counter(
    'chatbot_helpdesk_recap_total',
    'Helpdesk conversation-recap calls by outcome',
    ['outcome'],  # success | llm_error | mock
)
HELPDESK_RECAP_LATENCY_SECONDS = Histogram(
    'chatbot_helpdesk_recap_latency_seconds',
    'Latency of the helpdesk conversation-recap call',
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10, 20),
)
HELPDESK_DRAFT_TICKET_TOTAL = Counter(
    'chatbot_helpdesk_draft_ticket_total',
    'Helpdesk structured-ticket-draft calls by outcome',
    ['outcome'],  # success | parse_error | llm_error | mock
)
HELPDESK_DRAFT_TICKET_LATENCY_SECONDS = Histogram(
    'chatbot_helpdesk_draft_ticket_latency_seconds',
    'Latency of the helpdesk structured-ticket-draft call',
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10, 20),
)
HELPDESK_CREATE_ISSUE_TOTAL = Counter(
    'chatbot_helpdesk_create_issue_total',
    'Helpdesk GitHub-issue creation by outcome',
    ['outcome'],  # success | github_error | deduplicated | disabled
)
HELPDESK_KB_RESOLVED_TOTAL = Counter(
    'chatbot_helpdesk_kb_resolved_total',
    'Count of chat completions tagged with the kb_resolved heuristic',
    ['value'],  # true | false | unknown
)
HELPDESK_AGENT_STARTED_TOTAL = Counter(
    'chatbot_helpdesk_agent_started_total',
    'Helpdesk agent sessions started by trigger',
    ['trigger'],  # api | chip | phrase | llm_router
)
HELPDESK_AGENT_TOOL_TOTAL = Counter(
    'chatbot_helpdesk_agent_tool_total',
    'Helpdesk agent tool calls by tool and outcome',
    ['tool', 'outcome', 'reason'],
)
HELPDESK_AGENT_TOOL_LATENCY_SECONDS = Histogram(
    'chatbot_helpdesk_agent_tool_latency_seconds',
    'Helpdesk agent tool latency by tool',
    ['tool'],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 20),
)
HELPDESK_AGENT_TOKENS_TOTAL = Counter(
    'chatbot_helpdesk_agent_tokens_total',
    'Estimated helpdesk agent tokens by node',
    ['node'],
)
HELPDESK_AGENT_DECISION_TOTAL = Counter(
    'chatbot_helpdesk_agent_decision_total',
    'Helpdesk agent supervisor decisions',
    ['next_action'],
)
HELPDESK_AGENT_TURNS_TAKEN = Histogram(
    'chatbot_helpdesk_agent_turns_taken',
    'Helpdesk agent turns taken by outcome',
    ['outcome'],
    buckets=(0, 1, 2, 3, 5, 8, 13),
)
HELPDESK_AGENT_OUTCOME_TOTAL = Counter(
    'chatbot_helpdesk_agent_outcome_total',
    'Helpdesk agent terminal outcomes',
    ['outcome'],  # draft_ready | linked | aborted | error
)
HELPDESK_AGENT_FUNNEL_TOTAL = Counter(
    'chatbot_helpdesk_agent_funnel_total',
    'Helpdesk agent funnel events by stage and outcome',
    ['stage', 'outcome'],
)
HELPDESK_AGENT_ERROR_TOTAL = Counter(
    'chatbot_helpdesk_agent_error_total',
    'Helpdesk agent errors by operation and reason',
    ['operation', 'reason'],
)


def normalized_path(request: Request) -> str:
    route = request.scope.get('route')
    if route and getattr(route, 'path', None):
        return route.path
    return request.url.path


async def metrics_middleware(request: Request, call_next) -> Response:
    method = request.method
    path = normalized_path(request)
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        REQUEST_EXCEPTIONS.labels(method=method, path=path).inc()
        REQUEST_COUNT.labels(method=method, path=path, status_code='500').inc()
        REQUEST_LATENCY_SECONDS.labels(method=method, path=path).observe(time.perf_counter() - started)
        raise
    status_code = str(response.status_code)
    REQUEST_COUNT.labels(method=method, path=path, status_code=status_code).inc()
    REQUEST_LATENCY_SECONDS.labels(method=method, path=path).observe(time.perf_counter() - started)
    return response


@contextmanager
def track_provider_latency(provider: str, operation: str):
    started = time.perf_counter()
    outcome = 'success'
    try:
        yield
    except Exception as exc:
        outcome = 'error'
        PROVIDER_ERRORS.labels(provider=provider, operation=operation, reason=exc.__class__.__name__).inc()
        raise
    finally:
        PROVIDER_LATENCY_SECONDS.labels(provider=provider, operation=operation, outcome=outcome).observe(time.perf_counter() - started)


def refresh_db_pool_metrics(engine: Engine) -> dict[str, float]:
    pool = getattr(engine, 'pool', None)
    if pool is None:
        return {}

    snapshot: dict[str, float] = {}
    for field in ('size', 'checkedout', 'checkedin', 'overflow'):
        method = getattr(pool, field, None)
        if callable(method):
            with suppress(TypeError, ValueError):
                snapshot[field] = float(method())

    if 'size' in snapshot:
        DB_POOL_SIZE.set(snapshot['size'])
    if 'checkedout' in snapshot:
        DB_POOL_CHECKED_OUT.set(snapshot['checkedout'])
    if 'checkedin' in snapshot:
        DB_POOL_CHECKED_IN.set(snapshot['checkedin'])
    if 'overflow' in snapshot:
        DB_POOL_OVERFLOW.set(snapshot['overflow'])

    max_conns = snapshot.get('size', 0.0) + max(0.0, snapshot.get('overflow', 0.0))
    if max_conns > 0:
        DB_POOL_USAGE_RATIO.set(snapshot.get('checkedout', 0.0) / max_conns)
    return snapshot


def metrics_response() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


def provider_error(provider: str, operation: str, reason: str) -> None:
    PROVIDER_ERRORS.labels(provider=provider, operation=operation, reason=reason).inc()
