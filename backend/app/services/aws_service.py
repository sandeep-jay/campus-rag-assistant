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

import boto3

from backend.app.core.config_manager import settings

logger = logging.getLogger(__name__)

"""AWS Service module for handling authentication and session management."""


class AWSService:
    """Service class for AWS operations and authentication."""

    @staticmethod
    def assume_role(region: str, role_arn: str):
        # Assumes an IAM role and returns a boto3 session.
        try:
            session = boto3.Session(region_name=region)
            sts_client = session.client('sts')
            assumed_role_object = sts_client.assume_role(RoleArn=role_arn, RoleSessionName='AssumeRoleSession1')
            credentials = assumed_role_object['Credentials']
            return boto3.Session(
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretAccessKey'],
                aws_session_token=credentials['SessionToken'],
                region_name=region,
            )
        except Exception as e:
            logger.error(f'AWS Authentication Error: {e}')
            return None

    @staticmethod
    def get_session():
        # Get an AWS session based on application configuration.
        try:
            # If role ARN is provided, use role-based authentication
            if settings.AWS_ROLE_ARN:
                return AWSService.assume_role(region=settings.AWS_REGION, role_arn=settings.AWS_ROLE_ARN)

        except Exception as e:
            logger.error(f'Failed to create AWS session: {e}')
            return None
