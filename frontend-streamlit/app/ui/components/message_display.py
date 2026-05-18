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
from typing import Any

import streamlit as st

from ...logger import logger
from ..styles import load_sources_styles
from .feedback import display_feedback_options

"""Components for displaying chat messages."""


def truncate_text(text: str, word_limit: int = 100) -> str:
    # Truncate text to a specified word limit.
    words = text.split()
    if len(words) <= word_limit:
        return text

    truncated = ' '.join(words[:word_limit])
    return f'{truncated} (... more)'


def _display_assistant_message_id(message: dict[str, Any]) -> None:
    # Display the message ID for assistant messages.
    if message['role'] == 'assistant':
        if 'id' in message:
            # Show the message ID more prominently with debug mode
            if st.session_state.get('show_feedback_debug', False):
                st.info(f"Message ID: {message['id']} (Use this ID for feedback testing)")
            else:
                st.caption(f"Message ID: {message['id']}")
        else:
            st.caption('Warning: This message has no ID')


def _handle_feedback_options(message: dict[str, Any], timestamp: int) -> None:
    # Handle the display of feedback options for assistant messages.
    if message['role'] != 'assistant':
        return

    if 'id' in message:
        message_id = message['id']
        # Ensure message_id is always an integer
        if isinstance(message_id, str) and message_id.isdigit():
            message_id = int(message_id)
        logger.debug(
            f'Showing feedback options for assistant message with ID: {message_id}',
        )
        try:
            display_feedback_options(message_id, timestamp)
        except Exception as e:
            logger.exception(f'Error displaying feedback options: {e!s}')
            st.error(f'Failed to display feedback options: {e!s}')
    else:
        logger.warning(
            'Assistant message has no ID, cannot display feedback options',
        )
        st.write('⚠️ This message has no ID, feedback options are not available')


def _handle_message_menu(message: dict[str, Any], timestamp: int) -> None:
    # Handle the message context menu.
    # Create a unique key for the message
    message_key = f"msg_{hash(message['content'])}_{timestamp}"

    # Right-click menu (simulated with a small button)
    col1, col2 = st.columns([20, 1])
    with col2:
        if st.button('⋮', key=f'menu_{message_key}'):
            # In a real app you'd use JavaScript for right-click context menu
            # Here we just show a simple dropdown when the dots are clicked
            st.session_state[f'show_menu_{message_key}'] = True

    # Show delete option if menu is clicked
    if st.session_state.get(f'show_menu_{message_key}', False):
        if st.button('Delete Message', key=f'delete_{message_key}'):
            # In a real app, you'd also call an API to delete from the backend
            # Here we just remove from the local session state
            messages = st.session_state.get('messages', [])
            for i, msg in enumerate(messages):
                if msg.get('content') == message.get('content') and msg.get(
                    'role',
                ) == message.get('role'):
                    st.session_state.messages.pop(i)
                    break
            st.rerun()


def display_message(message: dict[str, Any]) -> None:
    # Display a chat message with appropriate styling and interactive elements.
    timestamp = int(time.time() * 1000)  # For unique component keys

    # Debug message content
    message_id = message.get('id')
    logger.debug(f"Displaying message: role={message['role']}, id={message_id}")

    # Create message container for right-click detection
    message_container = st.container()
    with message_container:
        with st.chat_message(message['role']):
            st.write(message['content'])

            # Add debug text to see message details in the app
            _display_assistant_message_id(message)

            # Only show feedback options for assistant messages
            _handle_feedback_options(message, timestamp)

            # Display metadata/sources if available
            if message.get('metadata'):
                display_message_metadata(message['metadata'])

        # Handle message menu (right-click functionality)
        _handle_message_menu(message, timestamp)


def display_message_metadata(metadata: Any) -> None:
    # Display message metadata such as sources.
    # Load source styles
    load_sources_styles()

    # Check if metadata is a dictionary with sources
    if isinstance(metadata, dict):
        sources = metadata.get('sources', [])
        source_documents = metadata.get('source_documents', [])
        document_contents = metadata.get('document_contents', [])

        if sources or source_documents or document_contents:
            # Create a subtle sources header
            st.markdown(
                """
            <div class="sources-container">
                <div style="display: flex; align-items: center; margin-bottom: 0.5em;">
                    <span style="font-size: 0.9em; margin-right: 5px;">🔍</span>
                    <span style="font-size: 0.9em; font-weight: normal; color: #666;">Sources</span>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

            # Create sources expander
            with st.expander('View all sources', expanded=False):
                if document_contents:
                    display_document_contents(document_contents)
                elif source_documents:
                    display_source_documents(source_documents)
                elif sources:
                    display_sources(sources)


def display_document_contents(document_contents: list[dict[str, Any]]) -> None:
    # Display document contents and metadata.
    tab1, tab2 = st.tabs(['Sources', 'Content'])

    # Sources tab - list of sources with URLs
    with tab1:
        for i, doc in enumerate(document_contents):
            metadata = doc.get('metadata', {})
            url = metadata.get('kb_url', '#')
            number = metadata.get('kb_number', 'N/A')
            category = metadata.get('kb_category', '')
            description = metadata.get('short_description', 'No title')
            project = metadata.get('project', '')
            score = metadata.get('score', None)  # Get retriever score

            # Source item with improved styling
            st.markdown(
                f"""
            <div class="source-item">
                <div style="font-size: 0.9em; color: #555; margin-bottom: 0.2em;">Source {i + 1}: {description}</div>
                {f'<div style="font-size: 0.85em;"><a href="{url}" target="_blank">{url}</a></div>' if url and url != '#' else ''}
                {f'<div style="font-size: 0.8em; color: #777;">KB: {number}</div>' if number and number != 'N/A' else ''}
                {f'<div style="font-size: 0.8em; color: #777;">Category: {category}</div>' if category else ''}
                {f'<div style="font-size: 0.8em; color: #777;">Project: {project}</div>' if project else ''}
                {f'<div style="font-size: 0.8em; color: #777;">Score: {score:.3f}</div>' if score is not None else ''}
            </div>
            <hr style="margin: 0.5em 0; border-color: #eaeaea; height: 1px;">
            """,
                unsafe_allow_html=True,
            )

    # Content tab - full content of each source
    with tab2:
        for i, doc in enumerate(document_contents):
            metadata = doc.get('metadata', {})
            content = doc.get('content', 'No content available')
            score = metadata.get('score', None)  # Get retriever score
            description = metadata.get('short_description', 'No title')

            # Source content with improved styling
            with st.container():
                # Use short_description as title
                st.markdown(
                    f"""
                <div style="font-size: 0.9em; color: #555; margin-bottom: 0.2em;">
                    {description}
                    {f'<span style="font-size: 0.8em; color: #777; margin-left: 0.5em;">(Score: {score:.3f})</span>' if score is not None else ''}
                </div>
                """,
                    unsafe_allow_html=True,
                )

                # Metadata section as a simple line
                metadata_parts = []
                url = metadata.get('kb_url', '#')
                if url and url != '#':
                    metadata_parts.append(
                        f'<a href="{url}" target="_blank">View Source</a>',
                    )

                number = metadata.get('kb_number', '')
                if number and number != 'N/A':
                    metadata_parts.append(f'KB: {number}')  # Removed KB# prefix

                category = metadata.get('kb_category', '')
                if category:
                    metadata_parts.append(f'Category: {category}')

                if metadata_parts:
                    st.markdown(
                        f'<div style="font-size: 0.8em; color: #777; margin-bottom: 0.3em;">{" | ".join(metadata_parts)}</div>',
                        unsafe_allow_html=True,
                    )

                # Content with improved styling for readability
                content_text = truncate_text(content)
                st.markdown(
                    f'<div style="font-size: 0.85em; color: #333; background-color: #f9f9f9; '
                    f'padding: 0.8em; border-radius: 4px; line-height: 1.4;">{content_text}</div>',
                    unsafe_allow_html=True,
                )

                st.markdown(
                    '<hr style="margin: 0.8em 0; border-color: #eaeaea; height: 1px;">',
                    unsafe_allow_html=True,
                )


def display_source_documents(source_documents: list[dict[str, Any]]) -> None:
    # Display source documents metadata.
    tab1, tab2 = st.tabs(['Sources', 'Content'])

    # Sources tab - list of sources with URLs
    with tab1:
        for i, doc in enumerate(source_documents):
            metadata = doc.get('metadata', {})
            url = metadata.get('kb_url', '#')
            number = metadata.get('kb_number', 'N/A')
            category = metadata.get('kb_category', '')
            description = metadata.get('short_description', 'No title')
            project = metadata.get('project', '')
            score = metadata.get('score', None)  # Get retriever score

            # Source item with improved styling
            st.markdown(
                f"""
            <div class="source-item">
                <div style="font-size: 0.9em; color: #555; margin-bottom: 0.2em;">Source {i + 1}: {description}</div>
                {f'<div style="font-size: 0.85em;"><a href="{url}" target="_blank">{url}</a></div>' if url and url != '#' else ''}
                {f'<div style="font-size: 0.8em; color: #777;">Number: {number}</div>' if number and number != 'N/A' else ''}
                {f'<div style="font-size: 0.8em; color: #777;">Category: {category}</div>' if category else ''}
                {f'<div style="font-size: 0.8em; color: #777;">Project: {project}</div>' if project else ''}
                {f'<div style="font-size: 0.8em; color: #777;">Score: {score:.3f}</div>' if score is not None else ''}
            </div>
            <hr style="margin: 0.5em 0; border-color: #eaeaea; height: 1px;">
            """,
                unsafe_allow_html=True,
            )

    # Content tab - full content of each source
    with tab2:
        for i, doc in enumerate(source_documents):
            metadata = doc.get('metadata', {})
            description = metadata.get('short_description', 'No title')
            content = doc.get('page_content', 'No content available')
            score = metadata.get('score', None)  # Get retriever score

            # Source content with improved styling
            with st.container():
                # Source title - use short_description instead of "Source N"
                st.markdown(
                    f"""
                    <div style="font-size: 0.9em; color: #555; margin-bottom: 0.2em;">
                        {description}
                        {f'<span style="font-size: 0.8em; color: #777; margin-left: 0.5em;">(Score: {score:.3f})</span>' if score is not None else ''}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Metadata as a simple line
                metadata_parts = []
                url = metadata.get('kb_url', '#')
                if url and url != '#':
                    metadata_parts.append(
                        f'<a href="{url}" target="_blank">View Source</a>',
                    )

                number = metadata.get('kb_number', '')
                if number and number != 'N/A':
                    metadata_parts.append(f'KB: {number}')  # Removed KB# prefix

                category = metadata.get('kb_category', '')
                if category:
                    metadata_parts.append(f'Category: {category}')

                if metadata_parts:
                    st.markdown(
                        f'<div style="font-size: 0.8em; color: #777; margin-bottom: 0.3em;">{" | ".join(metadata_parts)}</div>',
                        unsafe_allow_html=True,
                    )

                # Content with improved styling for readability
                content_text = truncate_text(content)
                st.markdown(
                    f'<div style="font-size: 0.85em; color: #333; background-color: #f9f9f9; '
                    f'padding: 0.8em; border-radius: 4px; line-height: 1.4;">{content_text}</div>',
                    unsafe_allow_html=True,
                )

                st.markdown(
                    '<hr style="margin: 0.8em 0; border-color: #eaeaea; height: 1px;">',
                    unsafe_allow_html=True,
                )


def display_sources(sources: list[dict[str, Any]]) -> None:
    # Display sources metadata.
    for i, source in enumerate(sources):
        kb_url = source.get('kb_url', '#')
        kb_number = source.get('kb_number', 'N/A')
        kb_category = source.get('kb_category', '')
        short_description = source.get('short_description', 'No title')
        project = source.get('project', '')
        score = source.get('score', None)  # Get retriever score

        # Source item with improved styling
        st.markdown(
            f"""
        <div class="source-item">
            <div style="display: flex; align-items: center;">
                <span style="font-size: 0.8em; color: #777; margin-right: 0.5em;">{i + 1}.</span>
                <div style="font-size: 0.9em; color: #555;">{short_description}</div>
                {f'<span style="font-size: 0.8em; color: #777; margin-left: 0.5em;">(Score: {score:.3f})</span>' if score is not None else ''}
            </div>
            {
                f'<div style="font-size: 0.85em; margin-top: 0.2em;">' f'<a href="{kb_url}" target="_blank">{kb_url}</a></div>'
                if kb_url and kb_url != '#'
                else ''
            }
            <div style="display: flex; flex-wrap: wrap; gap: 0.5em; margin-top: 0.2em;">
                {f'<span style="font-size: 0.8em; color: #777;">Category: {kb_category}</span>' if kb_category else ''}
                {f'<span style="font-size: 0.8em; color: #777;">KB: {kb_number}</span>' if kb_number and kb_number != 'N/A' else ''}
                {f'<span style="font-size: 0.8em; color: #777;">Project: {project}</span>' if project else ''}
            </div>
        </div>
        <hr style="margin: 0.5em 0; border-color: #eaeaea; height: 1px;">
        """,
            unsafe_allow_html=True,
        )
