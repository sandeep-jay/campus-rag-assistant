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

"""CSS styles for the profile components."""


def load_profile_styles() -> None:
    # Load the profile UI component styles.
    st.markdown(
        """
        <style>
        /* Profile container */
        .profile-container {
            display: flex;
            align-items: center;
            padding: 0.5em;
            margin-bottom: 1em;
            border-bottom: 1px solid #eaeaea;
        }

        /* Profile picture */
        .profile-pic {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            margin-right: 1em;
            object-fit: cover;
        }

        /* Profile name */
        .profile-name {
            font-size: 1em;
            font-weight: 500;
            margin: 0;
        }

        /* Profile options */
        .profile-options {
            margin-top: 0.5em;
        }

        /* Profile button */
        .profile-button {
            font-size: 0.9em;
            padding: 0.3em 0.6em;
            margin: 0.3em 0;
            border: 1px solid #ddd;
            border-radius: 4px;
            background-color: #f9f9f9;
            transition: all 0.2s;
        }
        .profile-button:hover {
            background-color: #f0f0f0;
        }

        /* Profile menu */
        .profile-menu {
            margin-top: 0.5em;
            border: 1px solid #eaeaea;
            border-radius: 4px;
            padding: 0.5em;
        }

        /* Profile menu item */
        .profile-menu-item {
            padding: 0.3em 0.6em;
            font-size: 0.9em;
            cursor: pointer;
            transition: all 0.2s;
        }
        .profile-menu-item:hover {
            background-color: #f0f0f0;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )
