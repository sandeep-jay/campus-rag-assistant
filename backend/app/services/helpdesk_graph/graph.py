"""Compiled LangGraph StateGraph for the helpdesk agent.

This module gives the helpdesk agent a real LangGraph tree (one tree per
session) so LangSmith shows nested supervisor / tool / specialist spans
instead of one flat span from the imperative runner.

User-visible behaviour is unchanged: every node delegates to the helpers
already living in :mod:`backend.app.services.helpdesk_graph.runner`, so
``debug_trace``, ``AgentTurn`` shape, and the ``/api/helpdesk/agent/*``
contract remain byte-identical. Phase 1b compiles this graph with a real
LangGraph checkpointer and uses ``interrupt()`` for user/HITL pause points.

Routing key. The supervisor writes its choice to ``state['_next']``
(a transient key stripped before checkpoint save). Using a separate
routing key avoids collisions with ``state['next_action']``, which the
helpers still set to persistent values such as ``await_user_confirm``
and which the confirm endpoint validates against.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from backend.app.core.config_manager import settings
from backend.app.core.metrics import HELPDESK_AGENT_DECISION_TOTAL
from backend.app.services.helpdesk_graph.checkpoint import (
    checkpointer_context,
    use_langgraph_checkpoint,
)
from backend.app.services.helpdesk_graph.nodes import (
    select_supervisor_action,
    validate_supervisor_action,
)
from backend.app.services.helpdesk_graph.state import HelpdeskState

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from langgraph.graph.state import CompiledStateGraph


# Map each :class:`SupervisorAction` value to the graph node it routes to.
# ``end`` is the terminator the supervisor picks once a turn has been
# produced (``state['_graph_turn']`` is non-empty), so the graph stops
# without looping.
_ACTION_TO_NODE: dict[str, str] = {
    'search_duplicates': 'tools',
    'link_existing': 'link_existing',
    'ask_user': 'clarifier',
    'propose_solution': 'solution',
    'resolved_by_agent': 'resolved',
    'write_draft': 'classifier',
    'file_new': 'file_ticket',
    'abort': 'aborted',
    'end': END,
}


def _route_supervisor(state: HelpdeskState) -> str:
    action = state.get('_next') or 'end'
    return _ACTION_TO_NODE.get(action, END)


def _route_after_specialist(state: HelpdeskState) -> str:
    """Route turn-producing specialists to the right pause node.

    ``clarifier``, ``solution`` and ``writer`` all emit an
    ``AgentTurn``; whether the agent is now waiting on a user reply
    (``await_user``) or HITL confirmation (``await_confirm``) is
    determined by the turn kind. Phase 1b replaces these no-op pause
    nodes with ``langgraph.types.interrupt()`` calls.
    """
    turn = state.get('_graph_turn')
    if turn is None:
        if state.get('_next') is not None:
            return 'supervisor'
        return END
    if turn.kind == 'draft_ready':
        return 'await_confirm'
    if turn.kind in {'question', 'info'}:
        return 'await_user'
    return END


def _route_after_classifier(state: HelpdeskState) -> str:
    if state.get('_next') == 'ask_user':
        return 'clarifier'
    return 'writer'


async def _supervisor_node(state: HelpdeskState) -> dict[str, Any]:
    if settings.HELPDESK_AGENT_LLM_SUPERVISOR:
        try:
            from backend.app.services.helpdesk_graph.llm import supervisor_decide

            decision = await supervisor_decide(state)
            action = validate_supervisor_action(state, getattr(decision, 'next_action', None))
            if action is not None:
                HELPDESK_AGENT_DECISION_TOTAL.labels(next_action=action).inc()
                return {'_next': action}
            fallback = 'end' if state.get('_graph_turn') is not None else 'write_draft'
            HELPDESK_AGENT_DECISION_TOTAL.labels(next_action=fallback).inc()
            return {'_next': fallback}
        except Exception:
            # Supervisor failures must never escape to the user; the
            # deterministic supervisor remains the rollback path.
            return {'_next': select_supervisor_action(state)}
    return {'_next': select_supervisor_action(state)}


async def _tools_node(state: HelpdeskState) -> dict[str, Any]:
    """Dispatch the agent's deterministic tools.

    Phase 1a only routes ``search_duplicates`` through this node — the
    other tools (``retry_kb`` / ``web_search``) run inside
    ``_propose_solution_or_draft`` and we keep that helper intact so
    the trace byte-shape matches the pre-graph runner. Phase 2 replaces
    this hand-rolled dispatcher with a LangGraph ``ToolNode`` bound to
    ``@tool``-decorated wrappers around the same callables.
    """
    from backend.app.services.helpdesk_graph import runner as _runner

    action = state.get('_next')
    if action == 'search_duplicates':
        duplicates = await _runner.graph_tool_search_duplicates(dict(state))
        return {'duplicate_candidates': duplicates}
    return {}


async def _clarifier_node(state: HelpdeskState) -> dict[str, Any]:
    from backend.app.services.helpdesk_graph import runner as _runner

    return await _runner.graph_clarifier_step(dict(state))


async def _classifier_node(state: HelpdeskState) -> dict[str, Any]:
    from backend.app.services.helpdesk_graph import runner as _runner

    return await _runner.graph_classifier_step(dict(state))


async def _writer_node(state: HelpdeskState) -> dict[str, Any]:
    from backend.app.services.helpdesk_graph import runner as _runner

    return await _runner.graph_writer_step(dict(state))


async def _solution_node(state: HelpdeskState) -> dict[str, Any]:
    from backend.app.services.helpdesk_graph import runner as _runner

    return await _runner.graph_solution_step(dict(state))


async def _link_existing_node(state: HelpdeskState) -> dict[str, Any]:
    from backend.app.services.helpdesk_graph import runner as _runner

    return await _runner.graph_link_existing_step(dict(state))


async def _file_ticket_node(state: HelpdeskState) -> dict[str, Any]:
    from backend.app.services.helpdesk_graph import runner as _runner

    return await _runner.graph_file_ticket_step(dict(state))


async def _resolved_node(state: HelpdeskState) -> dict[str, Any]:
    from backend.app.services.helpdesk_graph import runner as _runner

    return await _runner.graph_resolved_step(dict(state))


async def _aborted_node(state: HelpdeskState) -> dict[str, Any]:
    from backend.app.services.helpdesk_graph import runner as _runner

    return await _runner.graph_aborted_step(dict(state))


async def _await_user_node(state: HelpdeskState) -> dict[str, Any]:
    """Pause point: agent is awaiting a user reply.

    With the LangGraph checkpointer enabled, this node interrupts the graph
    and the API later resumes it with ``Command(resume=...)``. The rollback
    path leaves it as a no-op so the legacy JSON checkpoint flow can keep
    returning the already-produced ``AgentTurn``.
    """
    if not use_langgraph_checkpoint():
        return {}
    payload = state.get('awaiting_user')
    resume_value = interrupt(
        {
            'kind': 'await_user',
            'question_id': payload.question_id if payload is not None else None,
            'question': payload.question if payload is not None else None,
            'choices': payload.choices if payload is not None else [],
        }
    )
    if isinstance(resume_value, dict) and resume_value.get('action') == 'abort':
        return {'entry': 'abort', '_graph_turn': None}
    return {
        'entry': 'resume',
        'resume_answer': str(resume_value or ''),
        '_graph_turn': None,
    }


async def _await_confirm_node(state: HelpdeskState) -> dict[str, Any]:
    """Pause point: agent is awaiting HITL confirmation of a draft."""
    if not use_langgraph_checkpoint():
        return {}
    resume_value = interrupt(
        {
            'kind': 'await_confirm',
            'draft_ready': state.get('draft') is not None,
        }
    )
    if isinstance(resume_value, dict) and resume_value.get('action') == 'abort':
        return {'entry': 'abort', '_graph_turn': None}

    from backend.app.schemas.helpdesk import TicketDraft

    draft = resume_value if isinstance(resume_value, TicketDraft) else TicketDraft(**resume_value)
    return {'entry': 'confirm', 'confirm_draft': draft, '_graph_turn': None}


def build_helpdesk_graph(*, checkpointer: Any | None = None) -> CompiledStateGraph:
    """Compile the helpdesk agent StateGraph.

    The graph is compiled once at import time and reused for every
    session. Each invocation reads its inputs from the typed state dict
    the runner seeds (``entry``, ``resume_answer``, ``confirm_draft``)
    and writes its final ``AgentTurn`` to ``state['_graph_turn']``.
    """
    graph = StateGraph(HelpdeskState)

    graph.add_node('supervisor', _supervisor_node)
    graph.add_node('tools', _tools_node)
    graph.add_node('clarifier', _clarifier_node)
    graph.add_node('classifier', _classifier_node)
    graph.add_node('writer', _writer_node)
    graph.add_node('solution', _solution_node)
    graph.add_node('await_user', _await_user_node)
    graph.add_node('await_confirm', _await_confirm_node)
    graph.add_node('link_existing', _link_existing_node)
    graph.add_node('file_ticket', _file_ticket_node)
    graph.add_node('resolved', _resolved_node)
    graph.add_node('aborted', _aborted_node)

    graph.add_edge(START, 'supervisor')
    graph.add_conditional_edges('supervisor', _route_supervisor)

    graph.add_edge('tools', 'supervisor')
    graph.add_conditional_edges('classifier', _route_after_classifier)

    for specialist in ('clarifier', 'solution', 'writer'):
        graph.add_conditional_edges(specialist, _route_after_specialist)

    graph.add_edge('await_user', 'supervisor')
    graph.add_edge('await_confirm', 'supervisor')

    for terminal in ('link_existing', 'file_ticket', 'resolved', 'aborted'):
        graph.add_edge(terminal, END)

    return graph.compile(checkpointer=checkpointer)


@asynccontextmanager
async def helpdesk_graph_for_request() -> AsyncIterator[CompiledStateGraph]:
    """Yield a graph compiled for the configured checkpoint backend."""
    if not use_langgraph_checkpoint():
        yield HELPDESK_GRAPH
        return
    async with checkpointer_context() as checkpointer:
        yield build_helpdesk_graph(checkpointer=checkpointer)


HELPDESK_GRAPH: CompiledStateGraph = build_helpdesk_graph()
