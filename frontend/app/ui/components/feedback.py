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

import time

import streamlit as st

from ...chat import submit_message_feedback
from ...logger import logger
from ..styles import load_feedback_styles

"""Feedback UI components for message feedback and rating."""


def _submit_thumbs_up(message_id: int) -> None:
    # Submit a thumbs up feedback.
    logger.debug(f'Submitting thumbs up for message {message_id}')

    # This function should only be responsible for API submission, not toggling state
    if st.session_state.get(f'feedback_{message_id}') == 'thumbs_up':
        # Toggle off if already active
        logger.debug(f'Toggling off thumbs up for message {message_id}')
        success = submit_message_feedback(message_id=message_id, feedback_type='thumbs_up', rating=None)
        if success:
            st.session_state[f'feedback_{message_id}'] = None
            st.session_state[f'feedback_status_{message_id}'] = None
        else:
            st.session_state[f'feedback_status_{message_id}'] = 'Failed to toggle feedback'
    else:
        # Submit new feedback
        success = submit_message_feedback(message_id=message_id, feedback_type='thumbs_up', rating=None)

        if success:
            logger.debug(f'Successfully submitted thumbs up for message {message_id}')
            st.session_state[f'feedback_{message_id}'] = 'thumbs_up'
            st.session_state[f'feedback_status_{message_id}'] = 'Thanks for your feedback! 👍'
        else:
            logger.error(f'Failed to submit thumbs up for message {message_id}')
            st.session_state[f'feedback_status_{message_id}'] = 'Failed to submit feedback'


def _submit_thumbs_down(message_id: int) -> None:
    # Submit a thumbs down feedback.
    logger.debug(f'Submitting thumbs down for message {message_id}')

    # This function should only be responsible for API submission, not toggling state
    if st.session_state.get(f'feedback_{message_id}') == 'thumbs_down':
        # Toggle off if already active
        logger.debug(f'Toggling off thumbs down for message {message_id}')
        success = submit_message_feedback(message_id=message_id, feedback_type='thumbs_down', rating=None)
        if success:
            st.session_state[f'feedback_{message_id}'] = None
            st.session_state[f'feedback_status_{message_id}'] = None
        else:
            st.session_state[f'feedback_status_{message_id}'] = 'Failed to toggle feedback'
    else:
        # Submit new feedback
        success = submit_message_feedback(message_id=message_id, feedback_type='thumbs_down', rating=None)

        if success:
            logger.debug(f'Successfully submitted thumbs down for message {message_id}')
            st.session_state[f'feedback_{message_id}'] = 'thumbs_down'
            st.session_state[f'feedback_status_{message_id}'] = "Thanks for your feedback! We'll try to improve."
        else:
            logger.error(f'Failed to submit thumbs down for message {message_id}')
            st.session_state[f'feedback_status_{message_id}'] = 'Failed to submit feedback'


def _display_basic_feedback_buttons(message_id: int, timestamp: int) -> None:
    # Display the basic feedback buttons (thumbs up/down, rating, comment).
    # Get current feedback state
    current_feedback = st.session_state.get(f'feedback_{message_id}', None)
    logger.debug(f'Displaying feedback buttons for message {message_id}, current state: {current_feedback}')

    # Show current feedback status if it exists
    status_key = f'feedback_status_{message_id}'
    if st.session_state.get(status_key):
        status_message = st.session_state[status_key]
        if 'Processing' in status_message or 'Submitting' in status_message:
            # Show a spinner for processing status
            with st.spinner(status_message):
                st.empty()
        else:
            # Show normal status message
            st.markdown(
                f'<div class="feedback-status">{status_message}</div>',
                unsafe_allow_html=True,
            )

    # Create columns for feedback buttons
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 8])

    # Thumbs up button
    with col1:
        thumbs_up_active = current_feedback == 'thumbs_up'
        button_label = '👍'
        button_type = 'primary' if thumbs_up_active else 'secondary'

        # Generate a unique key using message_id and timestamp
        unique_key = f'thumbs_up_{message_id}_{timestamp}'

        st.button(
            button_label,
            key=unique_key,
            help='This was helpful',
            type=button_type,
            on_click=_submit_thumbs_up,
            args=(message_id,),
        )

    # Thumbs down button
    with col2:
        thumbs_down_active = current_feedback == 'thumbs_down'
        button_label = '👎'
        button_type = 'primary' if thumbs_down_active else 'secondary'

        # Generate a unique key using message_id and timestamp
        unique_key = f'thumbs_down_{message_id}_{timestamp}'

        st.button(
            button_label,
            key=unique_key,
            help='This was not helpful',
            type=button_type,
            on_click=_submit_thumbs_down,
            args=(message_id,),
        )

    # Star rating button (just display, no functionality)
    with col3:
        button_label = '★'
        button_type = 'secondary'

        # Generate a unique key using message_id and timestamp
        unique_key = f'rating_{message_id}_{timestamp}'

        # Just display the button with no functionality
        st.button(
            button_label,
            key=unique_key,
            help='Rate this response',
            type=button_type,
            disabled=True,
        )

    # Comment button (just display, no functionality)
    with col4:
        button_label = '💭'
        button_type = 'secondary'

        # Generate a unique key using message_id and timestamp
        unique_key = f'comment_{message_id}_{timestamp}'

        # Just display the button with no functionality
        st.button(
            button_label,
            key=unique_key,
            help='Add a comment',
            type=button_type,
            disabled=True,
        )


def display_feedback_options(message_id: int, timestamp: int | None = None) -> None:
    # Display feedback options (thumbs up/down, star rating, comment) for a message.
    # Load feedback styles
    load_feedback_styles()

    # Always generate a fresh timestamp to ensure unique component keys
    # This helps prevent Streamlit's widget caching issues
    timestamp = int(time.time() * 1000) if timestamp is None else timestamp

    # Initialize session state for this message if not already done
    feedback_key = f'feedback_{message_id}'
    status_key = f'feedback_status_{message_id}'

    # Initialize all state keys if they don't exist
    if feedback_key not in st.session_state:
        st.session_state[feedback_key] = None
    if status_key not in st.session_state:
        st.session_state[status_key] = None

    # Display the basic feedback buttons
    _display_basic_feedback_buttons(message_id, timestamp)
