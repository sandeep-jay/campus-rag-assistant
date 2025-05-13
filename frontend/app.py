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

import logging
import os
from typing import Any

import requests
import streamlit as st

# Constants
API_BASE_URL = os.environ.get('API_BASE_URL', 'http://localhost:8000/api')
CHAT_ENDPOINT = f'{API_BASE_URL}/chat'

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# RTL Services Support Chatbot - Streamlit Frontend

# Session state initialization
if 'messages' not in st.session_state:
    st.session_state.messages = []


def send_chat_request(message: str, chat_history: list[dict[str, str]]):
    # Send a chat request to the API and get the response.
    try:
        payload = {'message': message, 'chat_history': chat_history}

        response = requests.post(
            CHAT_ENDPOINT,
            json=payload,
            timeout=60,  # Add 60 second timeout
        )

        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f'API request error: {e}')
        return {'answer': f'Error: Could not connect to the API. {e}', 'source_documents': []}


def display_source_documents(source_docs: list[dict[str, Any]]):
    # Display source documents in the Streamlit app.
    if source_docs:
        with st.expander('Sources'):
            for i, doc in enumerate(source_docs):
                st.markdown(f'**Source {i+1}:**')
                st.markdown(doc.get('page_content', 'No content available'))

                if metadata := doc.get('metadata', {}):
                    st.markdown('**Metadata:**')
                    for key, value in metadata.items():
                        st.markdown(f'- **{key}:** {value}')

                st.markdown('---')


# App UI
st.title('RTL Services Support Chat')
st.markdown('Ask any question about RTL services and resources!')

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message['role']):
        st.markdown(message['content'])

# Input for new message
if prompt := st.chat_input('How can I help you?'):
    # Add user message to chat history
    st.session_state.messages.append({'role': 'user', 'content': prompt})

    # Display the user message
    with st.chat_message('user'):
        st.markdown(prompt)

    # Get assistant response
    with st.chat_message('assistant'), st.spinner('Thinking...'):
        # Format chat history for the API
        chat_history = [
            {'role': msg['role'], 'content': msg['content']}
            for msg in st.session_state.messages[:-1]  # Exclude the current message
        ]

        # Call the API
        response = send_chat_request(prompt, chat_history)

        # Display the response
        st.markdown(response['answer'])

        # Display source documents if available
        display_source_documents(response.get('source_documents', []))

    # Add assistant response to chat history
    st.session_state.messages.append({'role': 'assistant', 'content': response['answer']})
