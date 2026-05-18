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
import pathlib
from typing import Any

from dotenv import load_dotenv

"""Configuration settings for the Streamlit application."""


def initialize_config():
    # Set up basic logging for configuration loading
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] - %(levelname)s: %(message)s',
    )
    _init_logger = logging.getLogger('config')

    # Load environment variables from project root
    _init_logger.info('Loading environment variables')
    # Get the path to the project root (two directories up from this file)
    root_dir = pathlib.Path(__file__).parent.parent.parent
    dotenv_path = root_dir / '.env'
    load_dotenv(dotenv_path=dotenv_path)
    _init_logger.info(f'Environment variables loaded from {dotenv_path}')

    # Log the core settings using basic logger
    _init_logger.info(f'API URL set to {settings.API_URL}')
    _init_logger.info(f'Logging level set to {settings.LOGGING_LEVEL}')
    _init_logger.info(f'Environment set to {settings.ENVIRONMENT}')


class Settings:
    """Application settings class."""

    # Core settings
    API_URL: str = os.getenv('API_URL', 'http://localhost:8000')

    # Logging settings
    LOGGING_LEVEL: str = os.getenv('LOGGING_LEVEL', 'INFO')
    LOGGING_FORMAT: str = os.getenv(
        'LOGGING_FORMAT',
        '[%(asctime)s] - %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]',
    )
    LOGGING_LOCATION: str = os.getenv('LOGGING_LOCATION', 'streamlit.log')
    LOGGING_PROPAGATION_LEVEL: str = os.getenv('LOGGING_PROPAGATION_LEVEL', 'INFO')
    LOG_TO_FILE: bool = os.getenv('LOG_TO_FILE', 'True').lower() in (
        'true',
        '1',
        't',
        'yes',
    )

    # Application settings
    ENVIRONMENT: str = os.getenv('ENVIRONMENT', 'development')

    def as_dict(self) -> dict[str, Any]:
        # Return configuration as a dictionary.
        return {key: value for key, value in self.__dict__.items() if not key.startswith('_') and key.isupper()}


# Create settings instance (singleton)
settings = Settings()

# For backwards compatibility
config = settings
