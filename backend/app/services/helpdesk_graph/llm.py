"""LLM adapters for the helpdesk graph.

This module hides provider differences from graph nodes. The public helpers
return typed decisions/facts and own all parse-repair/fallback behaviour so the
graph can stay a small state machine with a deterministic safety net.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from backend.app.services.helpdesk_graph import tools
from backend.app.services.helpdesk_graph.nodes import (
    SupervisorAction,
    allowed_supervisor_actions,
    classify_ticket_confidence,
    classify_ticket_facts,
    select_supervisor_action,
    validate_supervisor_action,
)
from backend.app.services.helpdesk_graph.prompts import CLARIFIER_PROMPT, CLASSIFIER_PROMPT, SUPERVISOR_PROMPT
from backend.app.services.helpdesk_graph.state import AwaitingUserPayload
from backend.app.services.providers import get_llm_provider

if TYPE_CHECKING:
    from backend.app.services.helpdesk_graph.state import HelpdeskState

logger = logging.getLogger(__name__)

IMPACT_QUESTION = 'Is this affecting only you, your team, or the whole campus?'
IMPACT_CHOICES = ['Only me', 'My team', 'Campus-wide', 'Not sure']


class SupervisorDecision(BaseModel):
    """Structured supervisor output from the live LLM path."""

    next_action: SupervisorAction
    reason: str = Field(min_length=1)
    args: dict[str, Any] = Field(default_factory=dict)


class TicketClassification(BaseModel):
    """Structured ticket facts returned by the classifier adapter."""

    severity: str = Field(pattern='^(low|medium|high|critical)$')
    category: str = Field(pattern='^(network|access|application|hardware|account|other)$')
    impact: str = Field(pattern='^(Single user|Team|Campus-wide)$')
    confidence: float = Field(ge=0.0, le=1.0)


class ClarifyingQuestion(BaseModel):
    """Structured clarifier output from the live LLM path."""

    question: str = Field(min_length=1)
    choices: list[str] = Field(default_factory=list)


def _state_brief(state: HelpdeskState) -> dict[str, Any]:
    awaiting = state.get('awaiting_user')
    return {
        'entry': state.get('entry'),
        'original_question': state.get('original_question', ''),
        'awaiting_user': awaiting.model_dump() if awaiting is not None else None,
        'duplicate_candidate_count': len(state.get('duplicate_candidates', [])) if 'duplicate_candidates' in state else None,
        'facts': state.get('facts', {}),
        'classification_confidence': state.get('classification_confidence'),
        'has_draft': state.get('draft') is not None,
        'turns_taken': state.get('turns_taken', 0),
        'questions_asked': state.get('questions_asked', []),
        'proposed_solution_count': len(state.get('proposed_solutions', [])),
        'allowed_actions': sorted(allowed_supervisor_actions(state)),
    }


def _fallback_decision(state: HelpdeskState, reason: str) -> SupervisorDecision:
    return SupervisorDecision(next_action=select_supervisor_action(state), reason=reason)


def _safe_default_decision(state: HelpdeskState, reason: str) -> SupervisorDecision:
    if state.get('_graph_turn') is not None:
        return SupervisorDecision(next_action='end', reason=reason)
    return SupervisorDecision(next_action='write_draft', reason=reason)


def validate_decision(state: HelpdeskState, decision: SupervisorDecision) -> SupervisorDecision:
    """Enforce enum membership and the current state's allow-list."""
    action = validate_supervisor_action(state, decision.next_action)
    if action is not None:
        return decision.model_copy(update={'next_action': action})
    return _safe_default_decision(state, f'invalid supervisor action blocked: {decision.next_action}')


async def _ainvoke(llm: Any, prompt: list[dict[str, str]]) -> Any:
    if hasattr(llm, 'ainvoke'):
        return await llm.ainvoke(prompt)
    return llm.invoke(prompt)


async def _structured_invoke(llm: Any, schema: type[BaseModel], prompt: list[dict[str, str]]) -> BaseModel:
    if not hasattr(llm, 'with_structured_output'):
        msg = f'{llm.__class__.__name__} does not support structured output'
        raise TypeError(msg)
    structured = llm.with_structured_output(schema)
    result = await _ainvoke(structured, prompt)
    if isinstance(result, schema):
        return result
    if isinstance(result, dict):
        return schema(**result)
    return schema.model_validate(result)


async def supervisor_decide(state: HelpdeskState) -> SupervisorDecision:
    """Return the next supervisor decision, with deterministic fallback."""
    provider = get_llm_provider()
    if provider.is_mock:
        return _fallback_decision(state, 'mock provider uses deterministic scripted supervisor')

    prompt = [
        {'role': 'system', 'content': SUPERVISOR_PROMPT},
        {
            'role': 'user',
            'content': (
                'Return one SupervisorDecision JSON object. '
                'Use only a next_action from the allowed_actions list in this state brief.\n\n'
                f'<state>{json.dumps(_state_brief(state), sort_keys=True)}</state>'
            ),
        },
    ]

    try:
        llm = provider.get_llm()
        if hasattr(llm, 'bind_tools'):
            bindable = tools.bindable_helpdesk_tools(
                state=state,
                user_id=state.get('user_id'),
                include_file_ticket=state.get('entry') == 'confirm',
            )
            llm = llm.bind_tools(bindable)
        decision = await _structured_invoke(llm, SupervisorDecision, prompt)
        return validate_decision(state, decision)
    except Exception as exc:
        logger.warning('Helpdesk supervisor structured output failed; retrying once: %s', exc)

    repair_prompt = [
        *prompt,
        {
            'role': 'user',
            'content': 'Your previous response did not parse or was unsafe. Return only a valid SupervisorDecision.',
        },
    ]
    try:
        llm = provider.get_llm()
        decision = await _structured_invoke(llm, SupervisorDecision, repair_prompt)
        return validate_decision(state, decision)
    except Exception as exc:
        logger.warning('Helpdesk supervisor repair failed; falling back to deterministic supervisor: %s', exc)
        return _fallback_decision(state, 'structured supervisor parse failed; deterministic fallback used')


async def classify(state: HelpdeskState) -> TicketClassification:
    """Classify ticket facts through the provider, falling back to keywords."""
    fallback = classify_ticket_facts(state)
    fallback_confidence = classify_ticket_confidence(state)
    provider = get_llm_provider()
    if provider.is_mock:
        return TicketClassification(**fallback, confidence=fallback_confidence)

    prompt = [
        {
            'role': 'system',
            'content': CLASSIFIER_PROMPT,
        },
        {'role': 'user', 'content': json.dumps(_state_brief(state), sort_keys=True)},
    ]
    try:
        classification = await _structured_invoke(provider.get_llm(), TicketClassification, prompt)
    except Exception as exc:
        logger.warning('Helpdesk classifier failed; using deterministic fallback: %s', exc)
        return TicketClassification(**fallback, confidence=min(fallback_confidence, 0.5))
    return classification


def _default_clarification(state: HelpdeskState) -> AwaitingUserPayload:
    return AwaitingUserPayload(
        question_id=f"impact-{state['session_id']}",
        question=IMPACT_QUESTION,
        choices=IMPACT_CHOICES,
    )


async def clarify(state: HelpdeskState) -> AwaitingUserPayload:
    """Build a targeted clarifying question, with deterministic fallback."""
    fallback = _default_clarification(state)
    provider = get_llm_provider()
    if provider.is_mock:
        return fallback

    prompt = [
        {'role': 'system', 'content': CLARIFIER_PROMPT},
        {
            'role': 'user',
            'content': (
                'Return one ClarifyingQuestion JSON object. '
                'If impact is the missing fact, include these choices exactly: '
                f'{IMPACT_CHOICES}.\n\n'
                f'<state>{json.dumps(_state_brief(state), sort_keys=True)}</state>'
            ),
        },
    ]
    try:
        question = await _structured_invoke(provider.get_llm(), ClarifyingQuestion, prompt)
    except Exception as exc:
        logger.warning('Helpdesk clarifier failed; using deterministic fallback: %s', exc)
        return fallback

    choices = question.choices or IMPACT_CHOICES
    return AwaitingUserPayload(
        question_id=f"impact-{state['session_id']}",
        question=question.question,
        choices=choices,
    )
