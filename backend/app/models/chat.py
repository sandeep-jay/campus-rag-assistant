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

import os

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON

from backend.app.db.database import Base


# Helper function to determine which JSON type to use based on environment
def get_json_type():
    # Use JSON for SQLite tests, JSONB for PostgreSQL
    if os.environ.get('TESTING', 'False').lower() == 'true':
        return JSON
    return JSONB


class ChatSession(Base):
    __tablename__ = 'chat_session'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    tenant_id = Column(
        Integer,
        ForeignKey('tenant.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    title = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship('User', back_populates='chat_sessions')
    tenant = relationship('Tenant', back_populates='chat_sessions')
    messages = relationship(
        'ChatMessage',
        back_populates='session',
        cascade='all, delete-orphan',
    )


class ChatMessage(Base):
    __tablename__ = 'chat_message'

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer,
        ForeignKey('chat_session.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    content = Column(Text, nullable=False)
    role = Column(String, nullable=False)
    message_meta = Column(JSONB, nullable=True)  # Using PostgreSQL JSONB
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    session = relationship('ChatSession', back_populates='messages')
    feedbacks = relationship(
        'Feedback',
        back_populates='message',
        cascade='all, delete-orphan',
    )


def get_json_column_type():
    # Use JSON for SQLite tests, JSONB for PostgreSQL
    if os.environ.get('TESTING', 'False').lower() == 'true':
        return JSON
    return JSONB
