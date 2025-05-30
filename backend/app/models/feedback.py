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

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from backend.app.db.database import Base


class Feedback(Base):
    __tablename__ = 'feedback'

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(
        Integer,
        ForeignKey('chat_message.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    feedback_type = Column(
        String,
        nullable=False,
    )  # 'thumbs_up', 'thumbs_down', 'rating'
    rating = Column(Integer, nullable=True)  # 1-4 star rating
    comment = Column(Text, nullable=True)
    run_id = Column(String, nullable=True)  # For LangSmith tracing
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    message = relationship('ChatMessage', back_populates='feedbacks')
    user = relationship('User', back_populates='feedbacks')

    def __repr__(self):
        return f'<Feedback(id={self.id}, message_id={self.message_id}, feedback_type={self.feedback_type}, rating={self.rating})>'
