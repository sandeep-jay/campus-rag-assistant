"""Graph nodes and supervisor routing for the helpdesk agent.

Phase 1a expands the legacy 3-branch ``supervisor_next_action`` into the
full ``NextAction`` enum so the compiled LangGraph supervisor can drive
every routing decision (start/resume/confirm/abort) through one entry
point. The supervisor stays deterministic — Phase 2 replaces it with an
LLM call that returns a structured ``SupervisorDecision``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from backend.app.services.helpdesk_graph.state import HelpdeskState

# Legacy alias kept for the small number of callers (and existing tests)
# that still expect the 3-branch Phase-A enum.
NextAction = Literal['search_duplicates', 'link_existing', 'write_draft']

# Full supervisor enum used by the compiled StateGraph. Values map 1:1
# to graph nodes via ``backend.app.services.helpdesk_graph.graph.route_supervisor``.
SupervisorAction = Literal[
    'search_duplicates',
    'link_existing',
    'ask_user',
    'propose_solution',
    'resolved_by_agent',
    'write_draft',
    'file_new',
    'abort',
    'end',
]


def supervisor_next_action(state: HelpdeskState) -> NextAction:
    """Legacy Phase-A supervisor: pick the next action from current state.

    Retained for back-compat with callers (and tests) that import this
    function directly. The full graph supervisor lives in
    :func:`select_supervisor_action`.
    """
    if 'duplicate_candidates' not in state:
        return 'search_duplicates'
    if state.get('duplicate_candidates'):
        return 'link_existing'
    return 'write_draft'


def _is_solution_acceptance(answer: str) -> bool:
    normalized = (answer or '').strip().lower()
    return normalized.startswith('yes') or 'solved' in normalized or 'fixed' in normalized


def _action_for_start(state: HelpdeskState) -> SupervisorAction:
    if not state.get('original_question'):
        return 'ask_user'
    if 'duplicate_candidates' not in state:
        return 'search_duplicates'
    if state.get('duplicate_candidates'):
        return 'link_existing'
    return 'ask_user'


def _action_for_resume(state: HelpdeskState) -> SupervisorAction:
    awaiting = state.get('awaiting_user')
    answer = state.get('resume_answer') or ''
    if awaiting is not None and awaiting.question_id.startswith('solution-'):
        return 'resolved_by_agent' if _is_solution_acceptance(answer) else 'write_draft'
    return 'propose_solution'


_ENTRY_DISPATCH: dict[str, SupervisorAction] = {
    'abort': 'abort',
    'confirm': 'file_new',
}


def select_supervisor_action(state: HelpdeskState) -> SupervisorAction:
    """Pick the next graph node from current state plus entry hint.

    This is the deterministic Phase 1a supervisor. It inspects:

    - ``entry`` — which API entry point invoked the graph this turn
      (``start``/``resume``/``confirm``/``abort``).
    - ``duplicate_candidates`` — whether the GitHub dup search has run.
    - ``awaiting_user`` — which pause the agent is resuming from
      (impact question vs proposed-solution feedback).
    - ``_graph_turn`` — set by terminal/pause nodes; signals END.

    Phase 2 swaps this for an LLM supervisor; the contract (state in,
    one ``SupervisorAction`` out) stays the same.
    """
    if state.get('_graph_turn') is not None:
        return 'end'
    entry = state.get('entry')
    if entry in _ENTRY_DISPATCH:
        return _ENTRY_DISPATCH[entry]
    if entry == 'start':
        return _action_for_start(state)
    if entry == 'resume':
        return _action_for_resume(state)
    return 'end'


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _classify_impact(text: str) -> str:
    if _contains_any(text, ('campus-wide', 'campus wide', 'all users', 'everyone', 'outage')):
        return 'Campus-wide'
    if _contains_any(text, ('my team', 'team', 'department', 'multiple users')):
        return 'Team'
    return 'Single user'


def _classify_severity(text: str) -> str:
    if _contains_any(text, ('outage', 'down', 'campus-wide', 'all users', 'everyone')):
        return 'critical'
    if _contains_any(text, ('blocked', 'cannot access', '403', 'forbidden', 'team', 'urgent')):
        return 'high'
    if _contains_any(text, ('cosmetic', 'typo', 'minor')):
        return 'low'
    return 'medium'


def _classify_category(text: str) -> str:
    category_rules = (
        ('network', ('wifi', 'vpn', 'network', 'internet')),
        ('access', ('403', 'forbidden', 'permission', 'login', 'password', 'access')),
        ('hardware', ('laptop', 'printer', 'monitor', 'keyboard', 'hardware')),
        ('account', ('account', 'username', 'profile')),
        ('application', ('oracle', 'financials', 'canvas', 'application', 'report')),
    )
    for category, markers in category_rules:
        if _contains_any(text, markers):
            return category
    return 'other'


def classify_ticket_facts(state: HelpdeskState) -> dict[str, str]:
    """Classify ticket facts from trusted conversation state.

    This deterministic Phase-D classifier is intentionally small and
    replaceable: it gives the graph an explicit specialist step and stable
    trace/facts contract before a later LLM classifier takes over.
    """
    conversation_text = ' '.join(turn.content for turn in state.get('conversation', []))
    facts_text = ' '.join(state.get('facts', {}).values())
    text = f"{state.get('original_question', '')} {conversation_text} {facts_text}".lower()

    return {
        'severity': _classify_severity(text),
        'category': _classify_category(text),
        'impact': _classify_impact(text),
    }
