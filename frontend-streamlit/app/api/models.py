"""
Copyright ©2025. The Regents of the University of California (Regents). All Rights Reserved.

Permission to use, copy, modify, and distribute this software and its documentation
for educational, research, and not-for-profit purposes, without fee and without a
signed licensing agreement, is hereby granted, provided that the above copyright
notice, this paragraph and the following two paragraphs appear in all copies,
modifications, and distributions.

Contact The Office of Technology Licensing, UC Berkeley, 2150 Shattuck Avenue,
Suite 510, Berkeley, CA 94720-1620, (510) 643-7201, otl@berkeley.edu,
http://ipira.berkeley.edu/industry-info for commercial licensing opportunities.

IN NO EVENT SHALL REGENTS BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT, SPECIAL,
INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING OUT OF
THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF REGENTS HAS BEEN ADVISED
OF THE POSSIBILITY OF SUCH DAMAGE.

REGENTS SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE
SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, PROVIDED HEREUNDER IS PROVIDED
"AS IS". REGENTS HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES,
ENHANCEMENTS, OR MODIFICATIONS.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

"""Data models for API communication."""


@dataclass
class User:
    """User data model."""

    username: str
    email: str | None = None
    id: int | None = None


@dataclass
class Message:
    """Chat message data model."""

    role: str
    content: str
    id: int | None = None
    created_at: datetime | None = None
    session_id: int | None = None
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        """Create a Message instance from a dictionary."""
        return cls(
            role=data.get('role', 'user'),
            content=data.get('content', ''),
            id=data.get('id'),
            created_at=datetime.fromisoformat(
                data.get('created_at', '').replace('Z', '+00:00'),
            )
            if data.get('created_at')
            else None,
            session_id=data.get('session_id'),
            metadata=data.get('metadata'),
        )


@dataclass
class ChatSession:
    """Chat session data model."""

    id: int
    title: str
    created_at: datetime
    messages: list[Message] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChatSession:
        """Create a ChatSession instance from a dictionary."""
        messages = []
        if 'messages' in data and isinstance(data['messages'], list):
            messages = [Message.from_dict(msg) for msg in data['messages']]

        return cls(
            id=data.get('id', 0),
            title=data.get('title', 'Untitled Chat'),
            created_at=datetime.fromisoformat(
                data.get('created_at', '').replace('Z', '+00:00'),
            )
            if data.get('created_at')
            else datetime.now(tz=UTC),
            messages=messages,
        )


@dataclass
class Feedback:
    """Feedback data model."""

    message_id: int
    feedback_type: str
    rating: int | None = None
    comment: str | None = None
