"""LangSmith tracing helpers for the helpdesk agent.

The ASK path is already traced via :mod:`backend.app.utils.simple_tracer`.
The agent runner, agent LLM calls, and agent tools were previously
untraced, so end-to-end visibility in LangSmith stopped at the chat layer.

This module provides two small primitives that wrap the
``langsmith.run_helpers.traceable`` decorator. Both are no-ops when
``LANGCHAIN_TRACING_V2`` is unset, so they are safe to apply
unconditionally and add zero runtime cost when tracing is disabled.

- :func:`trace_agent_run` — decorator for top-level agent operations
  (``start_session``, ``resume_session``, ``confirm_session``,
  ``abort_session``). Tags with ``helpdesk``, ``agent`` and a caller-
  supplied subtag (``start``, ``resume``, ...).
- :func:`trace_agent_tool` — decorator for the deterministic agent tools
  (KB retry, web search, GitHub issue search, file ticket) and the
  agent's LLM calls (solution summary, recap, draft ticket) so the run
  tree in LangSmith mirrors the agent's actual structure.

Both decorators support sync and async callables; ``traceable`` already
handles the async case natively. We additionally guard against missing
clients (e.g. ``LANGCHAIN_API_KEY`` not set) so production failures do
not leak through.
"""

from __future__ import annotations

import functools
import logging
from typing import TYPE_CHECKING, Any, TypeVar

from backend.app.core.config_manager import settings
from backend.app.utils.simple_tracer import get_client

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

T = TypeVar('T')


def _tracing_enabled() -> bool:
    return bool(settings.LANGCHAIN_TRACING_V2 and get_client() is not None)


def _wrap(
    func: Callable[..., Any],
    *,
    run_type: str,
    name: str,
    tags: list[str],
) -> Callable[..., Any]:
    """Return a `traceable`-wrapped function, or the original on failure."""
    if not _tracing_enabled():
        return func
    try:
        from langsmith.run_helpers import traceable

        return traceable(
            run_type=run_type,
            name=name,
            tags=tags,
            client=get_client(),
            project_name=settings.LANGCHAIN_PROJECT,
        )(func)
    except Exception as exc:  # tracing must never break the agent
        logger.warning('LangSmith tracing setup failed for %s: %s', name, exc)
        return func


def trace_agent_run(action: str) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorator for the four top-level agent entry points.

    ``action`` is the short name (``start``, ``resume``, ``confirm``,
    ``abort``) used to populate the LangSmith run name and tags. The
    decorated function is recorded as a ``chain`` run; nested tool calls
    appear underneath when they themselves use :func:`trace_agent_tool`.
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            traced = _wrap(
                func,
                run_type='chain',
                name=f'helpdesk_agent.{action}',
                tags=['helpdesk', 'agent', action],
            )
            return await traced(*args, **kwargs)

        return wrapper

    return decorator


def trace_agent_tool(name: str, *, run_type: str = 'tool') -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for agent tools and helper LLM calls.

    Use ``run_type='tool'`` for deterministic tools (KB retry, web
    search, GitHub search, file_ticket) and ``run_type='llm'`` for the
    helper LLM calls (solution summary, recap, draft ticket) so the
    LangSmith run tree distinguishes the two layers.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            traced = _wrap(func, run_type=run_type, name=name, tags=['helpdesk', 'agent', run_type])
            return traced(*args, **kwargs)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            traced = _wrap(func, run_type=run_type, name=name, tags=['helpdesk', 'agent', run_type])
            return await traced(*args, **kwargs)

        import inspect

        return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper

    return decorator
