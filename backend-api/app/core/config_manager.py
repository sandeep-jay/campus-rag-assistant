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
from pathlib import Path

from app.config.development import DevelopmentSettings
from app.config.test import TestSettings
from pydantic_settings import BaseSettings


class ConfigManager:
    """Application Config manager that implements the configuration precedence scheme."""

    def __init__(self):
        self.app_env = os.environ.get('APP_ENV', 'development').lower()
        self.local_configs_dir = os.environ.get('APP_LOCAL_CONFIGS')
        self.root_dir = Path(__file__).resolve().parent.parent.parent.parent
        self.settings = None

    def _get_settings_class(self):
        """Get the appropriate settings class based on APP_ENV."""
        if self.app_env == 'test':
            return TestSettings
        else:
            # Default to development if unknown environment
            return DevelopmentSettings

    def _find_env_files(self):
        """Find .env files in the following order.

        1. .env in APP_LOCAL_CONFIGS
        2. .env in root directory (chabot/)
        3. .env.{APP_ENV} in APP_LOCAL_CONFIGS
        4. .env.{APP_ENV} in root directory (chabot/)
        """
        env_files = []

        # Check for APP_LOCAL_CONFIGS first
        local_configs_dir = os.environ.get('APP_LOCAL_CONFIGS')
        if local_configs_dir:
            local_configs_path = Path(local_configs_dir)

            # Check for .env in APP_LOCAL_CONFIGS
            local_env_file = local_configs_path / '.env'
            if local_env_file.exists():
                env_files.append(str(local_env_file))

            # Check for .env.{APP_ENV} in APP_LOCAL_CONFIGS
            local_env_specific_file = local_configs_path / f'.env.{self.app_env}'
            if local_env_specific_file.exists():
                env_files.append(str(local_env_specific_file))

        # Then check root directory (chabot/) if files weren't found in APP_LOCAL_CONFIGS
        if not env_files or len(env_files) < 2:
            # Check for .env in root directory
            root_env_file = self.root_dir / '.env'
            if root_env_file.exists():
                env_files.append(str(root_env_file))

            # Check for .env.{APP_ENV} in root directory if not already found
            env_specific_pattern = f'.env.{self.app_env}'
            root_env_specific_file = self.root_dir / env_specific_pattern
            if root_env_specific_file.exists():
                env_files.append(str(root_env_specific_file))

        return env_files

    def load_config(self):
        """Load configuration according to the precedence scheme."""
        # Get appropriate settings class
        settings_class = self._get_settings_class()

        # Find all .env files in order of precedence
        env_files = self._find_env_files()

        # Create settings with env files
        settings = settings_class(
            _env_file=env_files,
            APP_ENV=self.app_env,
        )

        self.settings = settings
        return settings


# Settings class for direct use in applications
class Settings:
    """Settings class that provides access to configuration values.

    This is a wrapper around the BaseSettings instance created by ConfigManager.
    """

    def __init__(self, config_settings=None):
        if config_settings is None:
            config_manager = ConfigManager()
            config_settings = config_manager.load_config()

        # Set all attributes from the config settings
        for key, value in config_settings.model_dump().items():
            setattr(self, key, value)


# Create settings instance
settings = Settings()

# Export settings for direct use without modifying entire settings object
# Makes it easier to mock specific settings for testing
# Hides the implementation details of the ConfigManager and BaseSettings
PROJECT_NAME: str = settings.PROJECT_NAME
VERSION: str = settings.VERSION
API_V1_STR: str = settings.API_V1_STR
SECRET_KEY: str = settings.SECRET_KEY
ALGORITHM: str = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES
BACKEND_CORS_ORIGINS: list[str] = settings.BACKEND_CORS_ORIGINS
FRONTEND_URL: str = settings.FRONTEND_URL
SQLALCHEMY_DATABASE_URI: str | None = settings.SQLALCHEMY_DATABASE_URI
AWS_ACCESS_KEY_ID: str | None = settings.AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY: str | None = settings.AWS_SECRET_ACCESS_KEY
AWS_REGION: str = settings.AWS_REGION
AWS_ROLE_ARN: str | None = settings.AWS_ROLE_ARN
AWS_PROFILE_NAME: str | None = settings.AWS_PROFILE_NAME
BEDROCK_MODEL_ID: str = settings.BEDROCK_MODEL_ID
BEDROCK_KNOWLEDGE_BASE_ID: str | None = settings.BEDROCK_KNOWLEDGE_BASE_ID
LANGCHAIN_TRACING_V2: bool = settings.LANGCHAIN_TRACING_V2
LANGCHAIN_API_KEY: str | None = settings.LANGCHAIN_API_KEY
LANGCHAIN_PROJECT: str = settings.LANGCHAIN_PROJECT
LANGCHAIN_ENDPOINT: str | None = settings.LANGCHAIN_ENDPOINT
ENVIRONMENT: str = settings.ENVIRONMENT
APP_ENV: str | None = settings.APP_ENV
LOG_TO_FILE: bool = settings.LOG_TO_FILE
LOGGING_FORMAT: str = settings.LOGGING_FORMAT
LOGGING_LOCATION: str = settings.LOGGING_LOCATION
LOGGING_LEVEL: str = settings.LOGGING_LEVEL
LOGGING_PROPAGATION_LEVEL: str = settings.LOGGING_PROPAGATION_LEVEL
