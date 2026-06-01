"""Graph nodes and supervisor routing for the helpdesk agent.

Phase 1a expands the legacy 3-branch ``supervisor_next_action`` into the
full ``NextAction`` enum so the compiled LangGraph supervisor can drive
every routing decision (start/resume/confirm/abort) through one entry
point. The supervisor stays deterministic — Phase 2 replaces it with an
LLM call that returns a structured ``SupervisorDecision``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from backend.app.core.config_manager import settings

if TYPE_CHECKING:
    from backend.app.services.helpdesk_graph.state import HelpdeskState

# Legacy alias kept for the small number of callers (and existing tests)
# that still expect the 3-branch Phase-A enum.
NextAction = Literal['search_duplicates', 'link_existing', 'write_draft']

# Full supervisor enum used by the compiled StateGraph. Values map 1:1
# to graph nodes via ``backend.app.services.helpdesk_graph.graph.route_supervisor``.
SUPERVISOR_ACTIONS = (
    'search_duplicates',
    'link_existing',
    'ask_user',
    'propose_solution',
    'resolved_by_agent',
    'write_draft',
    'file_new',
    'abort',
    'end',
)
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
    if _should_try_solution_before_clarifying(state):
        return 'propose_solution'
    if _should_clarify_classification(state):
        return 'ask_user'
    return 'write_draft'


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


def _allowed_start_actions(state: HelpdeskState) -> set[SupervisorAction]:
    if not state.get('original_question'):
        return {'ask_user', 'write_draft', 'abort'}
    if 'duplicate_candidates' not in state:
        return {'search_duplicates', 'write_draft', 'abort'}
    if state.get('duplicate_candidates'):
        return {'link_existing', 'write_draft', 'abort'}
    if _should_try_solution_before_clarifying(state):
        return {'propose_solution', 'write_draft', 'abort'}
    if _should_clarify_classification(state):
        return {'ask_user', 'write_draft', 'abort'}
    return {'write_draft', 'abort'}


def allowed_supervisor_actions(state: HelpdeskState) -> set[SupervisorAction]:
    """Return the closed action allow-list for the current graph state."""
    if state.get('_graph_turn') is not None:
        actions: set[SupervisorAction] = {'end'}
    elif state.get('entry') == 'abort':
        actions = {'abort'}
    elif state.get('entry') == 'confirm':
        actions = {'file_new', 'abort'}
    elif state.get('entry') == 'resume':
        awaiting = state.get('awaiting_user')
        if awaiting is not None and awaiting.question_id.startswith('solution-'):
            actions = {'resolved_by_agent', 'write_draft', 'abort'}
        else:
            actions = {'propose_solution', 'write_draft', 'abort'}
    elif state.get('entry') == 'start':
        actions = _allowed_start_actions(state)
    else:
        actions = {'end'}
    return actions


def validate_supervisor_action(state: HelpdeskState, action: str | None) -> SupervisorAction | None:
    """Accept only enum members that are legal for this state."""
    if action not in SUPERVISOR_ACTIONS:
        return None
    typed_action = action  # type: ignore[assignment]
    if typed_action not in allowed_supervisor_actions(state):
        return None
    return typed_action


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


def _combined_classification_text(state: HelpdeskState) -> str:
    conversation_text = ' '.join(turn.content for turn in state.get('conversation', []))
    facts_text = ' '.join(state.get('facts', {}).values())
    return f"{state.get('original_question', '')} {conversation_text} {facts_text}".lower()


def _clarification_source_text(state: HelpdeskState) -> str:
    conversation_text = ' '.join(turn.content for turn in state.get('conversation', []))
    facts_text = ' '.join(value for key, value in state.get('facts', {}).items() if key not in {'severity', 'category', 'impact'})
    return f"{state.get('original_question', '')} {conversation_text} {facts_text}".lower()


def _has_explicit_impact(text: str) -> bool:
    return _contains_any(
        text,
        (
            'campus-wide',
            'campus wide',
            'all users',
            'everyone',
            'outage',
            'my team',
            'team',
            'department',
            'multiple users',
            'only me',
            'just me',
            'single user',
        ),
    )


def _classification_confidence(text: str, classification: dict[str, str]) -> float:
    confidence = 0.55
    if _has_explicit_impact(text):
        confidence += 0.25
    if classification['category'] != 'other':
        confidence += 0.1
    if classification['severity'] in {'high', 'critical', 'low'}:
        confidence += 0.1
    return min(confidence, 1.0)


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
    text = _combined_classification_text(state)

    return {
        'severity': _classify_severity(text),
        'category': _classify_category(text),
        'impact': _classify_impact(text),
    }


def classify_ticket_confidence(state: HelpdeskState) -> float:
    """Return a deterministic confidence score for keyword classification."""
    text = _combined_classification_text(state)
    return _classification_confidence(text, classify_ticket_facts(state))


def _positive_int_setting(name: str, default: int) -> int:
    value = int(getattr(settings, name, default) or default)
    return max(1, value)


def _clarify_confidence_floor() -> float:
    return float(getattr(settings, 'HELPDESK_AGENT_CLARIFY_CONFIDENCE_FLOOR', 0.75) or 0.75)


def _should_try_solution_before_clarifying(state: HelpdeskState) -> bool:
    return int(state.get('turns_taken', 0)) == 0 and not state.get('proposed_solutions') and int(state.get('tool_attempts', 0)) == 0


def _should_clarify_classification(state: HelpdeskState) -> bool:
    if 'classification_confidence' not in state:
        return False
    questions_asked = len(state.get('questions_asked', []))
    if questions_asked >= _positive_int_setting('HELPDESK_AGENT_MAX_QUESTIONS', 2):
        return False
    confidence = float(state.get('classification_confidence') or classify_ticket_confidence(state))
    if confidence >= _clarify_confidence_floor():
        return False
    return not _has_explicit_impact(_clarification_source_text(state))
