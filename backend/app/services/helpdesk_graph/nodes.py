"""Phase-A graph nodes for the helpdesk agent."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from backend.app.services.helpdesk_graph.state import HelpdeskState

NextAction = Literal['search_duplicates', 'link_existing', 'write_draft']


def supervisor_next_action(state: HelpdeskState) -> NextAction:
    """Pick the next Phase-A action from current state.

    This is intentionally deterministic in Phase A so tests can assert the
    branch shape before we wire the full LangGraph supervisor LLM.
    """
    if 'duplicate_candidates' not in state:
        return 'search_duplicates'
    if state.get('duplicate_candidates'):
        return 'link_existing'
    return 'write_draft'


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
