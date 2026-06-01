"""Compiled LangGraph StateGraph for the helpdesk agent (Phase 1a).

This module gives the helpdesk agent a real LangGraph tree (one tree per
session) so LangSmith shows nested supervisor / tool / specialist spans
instead of one flat span from the imperative runner.

User-visible behaviour is unchanged: every node delegates to the helpers
already living in :mod:`backend.app.services.helpdesk_graph.runner`, so
``debug_trace``, ``AgentTurn`` shape, and the ``/api/helpdesk/agent/*``
contract remain byte-identical. The compiled graph is what Phase 1b
swaps onto an ``AsyncPostgresSaver`` (replacing the bespoke
``checkpoint.py``) and Phase 2 extends with a real LLM supervisor and a
LangGraph ``ToolNode``.

Routing key. The supervisor writes its choice to ``state['_next']``
(a transient key stripped before checkpoint save). Using a separate
routing key avoids collisions with ``state['next_action']``, which the
helpers still set to persistent values such as ``await_user_confirm``
and which the confirm endpoint validates against.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langgraph.graph import END, START, StateGraph

from backend.app.services.helpdesk_graph.nodes import select_supervisor_action
from backend.app.services.helpdesk_graph.state import HelpdeskState

if TYPE_CHECKING:
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
    'write_draft': 'writer',
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
        return END
    if turn.kind == 'draft_ready':
        return 'await_confirm'
    if turn.kind in {'question', 'info'}:
        return 'await_user'
    return END


async def _supervisor_node(state: HelpdeskState) -> dict[str, Any]:
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
    """Phase 1a placeholder.

    The current ``_draft_from_state`` helper produces both the
    ``classify_ticket`` and ``write_draft`` trace steps in one call;
    splitting them into two graph nodes would change the trace
    byte-shape and break ``test_agent_solution_rejection_returns_ticket_draft``.
    Phase 2 splits the helper and routes through this node properly.
    """
    return {'_next': 'write_draft'}


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

    No-op in Phase 1a — the runner persists the awaiting payload via the
    bespoke checkpoint and returns control to the API. Phase 1b swaps
    this for ``langgraph.types.interrupt()`` so the resume path becomes
    ``Command(resume=...)`` instead of a custom dance.
    """
    return {}


async def _await_confirm_node(state: HelpdeskState) -> dict[str, Any]:
    """Pause point: agent is awaiting HITL confirmation of a draft."""
    return {}


def build_helpdesk_graph() -> CompiledStateGraph:
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
    graph.add_edge('classifier', 'writer')

    for specialist in ('clarifier', 'solution', 'writer'):
        graph.add_conditional_edges(specialist, _route_after_specialist)

    for terminal in ('await_user', 'await_confirm', 'link_existing', 'file_ticket', 'resolved', 'aborted'):
        graph.add_edge(terminal, END)

    return graph.compile()


HELPDESK_GRAPH: CompiledStateGraph = build_helpdesk_graph()
