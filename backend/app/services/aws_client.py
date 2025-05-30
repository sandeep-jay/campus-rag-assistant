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
import warnings

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, NoRegionError, ProfileNotFound

from backend.app.core.config_manager import settings

logger = logging.getLogger(__name__)


class AWSClientService:
    """Centralized AWS client management service"""

    def __init__(self, region_name=None, profile_name=None, role_arn=None):
        # Initialize the AWS client service

        if profile_name is not None:
            warnings.warn(
                'profile_name parameter is deprecated. When running on EC2, use instance profiles instead.', DeprecationWarning, stacklevel=2
            )
        self.region_name = region_name or settings.AWS_REGION
        self.profile_name = profile_name or settings.AWS_PROFILE_NAME  # kept for backward compatibility
        self.role_arn = role_arn or getattr(settings, 'AWS_ROLE_ARN', None)
        self.session = None
        self._initialize_session()

    def _initialize_session(self):
        # Initialize the AWS session
        try:
            # Only use role_arn if it's a string (not None, not a mock)
            if self.role_arn and isinstance(self.role_arn, str):
                logger.info(f'Initializing AWS session with role ARN: {self.role_arn}, region: {self.region_name}')
                # Create a base session first
                base_session = boto3.Session(
                    region_name=self.region_name,
                )

                # Use STS to assume the specified role
                sts_client = base_session.client('sts')

                # Generate a unique session name
                import uuid

                session_name = f'bedrock-service-{uuid.uuid4()}'

                try:
                    # Assume the role
                    response = sts_client.assume_role(
                        RoleArn=self.role_arn,
                        RoleSessionName=session_name,
                    )

                    # Extract temporary credentials
                    credentials = response['Credentials']

                    # Create a new session with the assumed role credentials
                    self.session = boto3.Session(
                        region_name=self.region_name,
                        aws_access_key_id=credentials['AccessKeyId'],
                        aws_secret_access_key=credentials['SecretAccessKey'],
                        aws_session_token=credentials['SessionToken'],
                    )
                    logger.info(f'Successfully assumed role {self.role_arn}')
                except ClientError as e:
                    logger.exception(f'Failed to assume role {self.role_arn}: {e!s}')
                    raise ValueError(f'Role assumption error: {e!s}')
            else:
                logger.info(f'Initializing AWS session with region: {self.region_name}')
                self.session = boto3.Session(
                    region_name=self.region_name,
                )
                logger.info('AWS session initialized successfully')
        except (ProfileNotFound, NoCredentialsError, NoRegionError) as e:
            logger.exception(f'AWS session initialization error: {e!s}')
            raise ValueError(f'AWS configuration error: {e!s}')

    def get_client(self, service_name):
        """Get an AWS client for the specified service"""
        if not self.session:
            raise RuntimeError('AWS session not initialized')

        logger.info(f'Creating {service_name} client')
        return self.session.client(service_name, region_name=self.region_name)
