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

import streamlit as st

"""CSS styles for the main application UI."""


def load_main_styles() -> None:
    # Load the main application styles.
    st.markdown(
        """
        <style>
        /* Main interface styles */
        .main-title {
            font-size: 1.5em;
            font-weight: 600;
            margin-bottom: 0.5em;
        }
        .main-description {
            font-size: 1em;
            color: #666;
            margin-bottom: 1.5em;
        }

        /* Chat message styles */
        div.stChatMessage {
            padding: 0.8em 1em;
            margin: 0.5em 0;
        }
        div.stChatMessage p {
            font-size: 0.95em;
            line-height: 1.4;
            margin: 0;
        }

        /* Sidebar styles */
        .sidebar-title {
            font-size: 1.2em;
            font-weight: 500;
            margin-bottom: 1em;
        }
        .chat-history-container {
            margin-top: 1em;
        }
        .chat-session {
            font-size: 0.9em;
            padding: 0.5em;
            margin: 0.3em 0;
            border: 1px solid #eee;
            border-radius: 4px;
        }

        /* Input field styles */
        .stTextInput input {
            font-size: 0.95em;
            padding: 0.5em;
        }

        /* Button styles */
        .stButton button {
            font-size: 0.9em;
            padding: 0.4em 0.8em;
        }

        /* Authentication form styles */
        div[data-testid="stForm"] {
            padding: 1em;
            background: #f8f9fa;
            border-radius: 4px;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )
