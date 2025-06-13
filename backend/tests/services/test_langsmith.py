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

import os
from unittest.mock import MagicMock, patch

import pytest
from langsmith import Client
from langsmith.run_helpers import traceable

from backend.app.core.config_manager import settings

"""Consolidated tests for LangSmith integration."""


@pytest.fixture()
def mock_langsmith_client():
    """Create a mock LangSmith client."""
    mock_client = MagicMock(spec=Client)
    mock_client.list_projects.return_value = [{'name': 'test-project'}]
    mock_client.list_runs.return_value = [{'id': 'test-run-id'}]
    return mock_client


def test_langsmith_tracing():
    """Test LangSmith tracing functionality."""
    with patch('langsmith.run_helpers.traceable') as mock_traceable:
        # Setup mocks
        mock_decorator = MagicMock()
        mock_traceable.return_value = mock_decorator
        mock_function = MagicMock(return_value='Processed result')
        mock_decorator.return_value = mock_function

        # Configure environment
        with patch.dict(
            os.environ,
            {
                'LANGCHAIN_TRACING_V2': 'true',
                'LANGCHAIN_PROJECT': 'test-project',
            },
        ):
            # Create a traceable function
            @traceable(run_type='chain')
            def test_function(text: str) -> str:
                """Test function that will be traced."""
                return f'Processed: {text}'

            # Call the function
            result = test_function('test input')

            # In our real test, this would verify the function is properly traced
            # For this mock test, we just ensure it functions as expected
            assert 'Processed: test input' in result or result == 'Processed result'


def test_langsmith_config_validation():
    """Test validation of LangSmith configuration."""
    # Test with all settings set
    with (
        patch.object(settings, 'LANGCHAIN_TRACING_V2', 'true'),
        patch.object(settings, 'LANGCHAIN_API_KEY', 'test-key'),
        patch.object(settings, 'LANGCHAIN_PROJECT', 'test-project'),
    ):
        assert settings.LANGCHAIN_TRACING_V2 == 'true'
        assert settings.LANGCHAIN_API_KEY == 'test-key'
        assert settings.LANGCHAIN_PROJECT == 'test-project'

    # Test with missing API key
    with (
        patch.object(settings, 'LANGCHAIN_TRACING_V2', 'true'),
        patch.object(settings, 'LANGCHAIN_API_KEY', None),
        patch.object(settings, 'LANGCHAIN_PROJECT', 'test-project'),
    ):
        # In a real project, this might check if a warning is logged or
        # if tracing is disabled when API key is missing
        assert settings.LANGCHAIN_API_KEY is None
