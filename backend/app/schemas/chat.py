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

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from .feedback import Feedback


class ChatMessageBase(BaseModel):
    content: str
    role: str
    message_meta: dict[str, Any] | None = None


class ChatMessageCreate(BaseModel):
    content: str
    session_id: int | None = None


class ChatMessage(ChatMessageBase):
    id: int
    session_id: int
    created_at: datetime
    feedbacks: list[Feedback] = []

    class Config:
        from_attributes = True


class ChatSessionBase(BaseModel):
    title: str


class ChatSessionCreate(ChatSessionBase):
    tenant_id: int | None = None


class ChatSession(ChatSessionBase):
    id: int
    user_id: int
    tenant_id: int | None = None
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessage] = []

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    message: str
    session_id: int | None = None
    tenant_id: int | None = None


class ChatResponse(BaseModel):
    message: str
    session_id: int
    message_meta: dict[str, Any] | None = None


class MessageFeedbackCreate(BaseModel):
    message_id: int
    rating: int  # 1-5 rating
    comment: str | None = None
    run_id: str | None = None  # For LangSmith tracing


class MessageFeedback(BaseModel):
    id: int
    message_id: int
    rating: int
    comment: str | None = None
    run_id: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class SourceDocument(BaseModel):
    # Model representing a source document.

    content: str
    metadata: dict[str, Any]
