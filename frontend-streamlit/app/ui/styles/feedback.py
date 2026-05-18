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

"""CSS styles for the feedback components."""


def load_feedback_styles() -> None:
    # Load the feedback UI component styles.
    st.markdown(
        """
        <style>
        /* Feedback container */
        .feedback-container {
            margin: 0.5em 0;
            padding: 0.8em;
            border: 1px solid #eaeaea;
            border-radius: 5px;
            background-color: #f9f9f9;
        }

        /* Feedback buttons container */
        .feedback-buttons {
            display: flex;
            gap: 0.5em;
            margin-bottom: 0.5em;
        }

        /* Horizontal layout for feedback buttons */
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            display: flex;
            justify-content: center;
            align-items: center;
        }
        div[data-testid="stHorizontalBlock"] button {
            background-color: transparent !important;
            border: none !important;
            color: #666 !important;
            box-shadow: none !important;
            font-size: 1.2em !important;
            padding: 0.3em 0.5em !important;
            min-width: auto !important;
        }
        div[data-testid="stHorizontalBlock"] button:hover {
            color: #ffd700 !important;
            transform: scale(1.1);
        }
        .feedback-active {
            color: #ffd700 !important;
        }

        /* Misc button styles */
        button[data-testid="baseButton-secondary"] {
            min-width: auto !important;
        }
        .feedback-status {
            font-size: 0.9em;
            color: #4CAF50;
            margin-top: 0.5em;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )
