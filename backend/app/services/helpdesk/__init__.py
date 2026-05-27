"""Helpdesk escalation package — post-RAG support flow.

Layers:
- ``schemas.helpdesk``: Pydantic request/response models.
- ``services.helpdesk.agent``: summarizer and draft-ticket LLM tasks (mock-friendly).
- ``services.helpdesk.github``: GitHub issue client (httpx, idempotent).
- ``services.helpdesk.redaction``: lightweight PII/secret scrubber.
- ``api.helpdesk``: FastAPI router (rate-limited, auth-required, feature-flagged).
"""
