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

import base64

import streamlit as st

from ...auth import get_user_info, logout
from ..styles import load_profile_styles

"""Profile UI components for displaying user information."""


def get_profile_pic(username: str) -> str:
    # Generate a placeholder profile picture with the first letter of username.
    first_letter = username[0].upper() if username else 'U'

    # Create a simple SVG for the profile pic
    colors = ['#3498db', '#9b59b6', '#e74c3c', '#2ecc71', '#f39c12']
    color = colors[hash(username) % len(colors)] if username else colors[0]

    svg = f"""
    <svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
        <circle cx="50" cy="50" r="45" fill="{color}" />
        <text x="50" y="60" font-size="45" text-anchor="middle" fill="white">{first_letter}</text>
    </svg>
    """

    svg_bytes = svg.encode()
    b64 = base64.b64encode(svg_bytes).decode()
    return f'data:image/svg+xml;base64,{b64}'


def display_profile_section(username: str) -> None:
    # Display a profile section with user information and options.
    # Load profile styles
    load_profile_styles()

    profile_pic = get_profile_pic(username)

    st.markdown(
        f"""
        <div class="profile-container">
            <img src="{profile_pic}" class="profile-pic">
            <h3 class="profile-name">{username}</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Profile dropdown as a separate element
    with st.expander('Profile Options', expanded=False):
        if st.button('Logout', key='logout_profile', use_container_width=True):
            logout()
            st.rerun()


def display_auth_user_profile() -> None:
    # Display the authenticated user's profile based on session state.
    # Get username from session state or API
    if 'username' in st.session_state and st.session_state.username:
        username = st.session_state.username
    else:
        user_info = get_user_info()
        username = user_info.get('username', 'User')
        st.session_state.username = username

    display_profile_section(username)
