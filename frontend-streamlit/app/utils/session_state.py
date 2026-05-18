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

from typing import Any

import streamlit as st

"""Utilities for managing Streamlit session state."""


def initialize_session_state() -> None:
    # Initialize the Streamlit session state with default values.
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if 'messages' not in st.session_state:
        st.session_state.messages = []

    if 'api_token' not in st.session_state:
        st.session_state.api_token = None

    if 'current_session_id' not in st.session_state:
        st.session_state.current_session_id = None

    if 'username' not in st.session_state:
        st.session_state.username = None


def add_message(message: dict[str, Any]) -> None:
    # Add a message to the session state.
    st.session_state.messages.append(message)


def clear_messages() -> None:
    # Clear all messages from the session state.
    st.session_state.messages = []


def set_current_session(session_id: int | None) -> None:
    # Set the current chat session ID.

    st.session_state.current_session_id = session_id


def set_logged_in(*, logged_in: bool) -> None:
    # Set the logged in state.

    st.session_state.logged_in = logged_in


def set_api_token(token: str | None) -> None:
    # Set the API token in session state.

    st.session_state.api_token = token


def set_username(username: str | None) -> None:
    # Set the username in session state.

    st.session_state.username = username


def clear_session_state() -> None:
    # Clear the session state completely.
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    initialize_session_state()
