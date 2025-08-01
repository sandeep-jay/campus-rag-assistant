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

"""CSS styles for the sources components."""


def load_sources_styles() -> None:
    """Load the sources UI component styles."""
    st.markdown(
        """
        <style>
        /* Sources section container */
        .sources-container {
            margin-top: 1em;
            padding: 0.8em;
            border-top: 1px solid #eaeaea;
        }

        /* Sources section title */
        .sources-section-title {
            font-size: 0.9em;
            font-weight: 500;
            color: #555;
            margin-bottom: 0.5em;
        }

        /* Individual source item */
        .source-item {
            margin-bottom: 0.5em;
            padding: 0.5em;
            border: 1px solid #eaeaea;
            border-radius: 4px;
            background-color: #f9f9f9;
        }

        /* Source title - smaller size to match response text */
        .source-title {
            font-size: 0.9em;
            font-weight: 500;
            color: #333;
            margin-bottom: 0.2em;
        }

        /* Source URL */
        .source-url {
            font-size: 0.8em;
            color: #1a73e8;
            word-break: break-all;
        }

        /* Source snippet */
        .source-snippet {
            font-size: 0.85em;
            color: #555;
            margin-top: 0.3em;
            line-height: 1.4;
        }

        /* Source relevance score */
        .source-score {
            font-size: 0.75em;
            color: #888;
            margin-top: 0.2em;
        }

        /* Source expand/collapse button */
        .source-toggle {
            font-size: 0.8em;
            color: #555;
            background: none;
            border: none;
            padding: 0.2em 0.5em;
            cursor: pointer;
            margin-top: 0.2em;
        }
        .source-toggle:hover {
            text-decoration: underline;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )
