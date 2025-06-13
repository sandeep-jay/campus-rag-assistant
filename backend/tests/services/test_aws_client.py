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

import warnings
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError, NoCredentialsError, NoRegionError, ProfileNotFound

from backend.app.services.aws_client import AWSClientService


@pytest.fixture()
def mock_boto3():
    with patch('backend.app.services.aws_client.boto3') as mock:
        mock_session = MagicMock()
        mock_session.client.return_value = MagicMock()
        mock.Session.return_value = mock_session
        yield mock


@pytest.fixture()
def mock_sts_client():
    mock_client = MagicMock()
    # Mock successful assume_role response
    mock_client.assume_role.return_value = {
        'Credentials': {
            'AccessKeyId': 'test-access-key',
            'SecretAccessKey': 'test-secret-key',
            'SessionToken': 'test-session-token',
            'Expiration': '2023-12-31T23:59:59Z',
        },
        'AssumedRoleUser': {
            'AssumedRoleId': 'test-role-id',
            'Arn': 'arn:aws:sts::123456789012:assumed-role/test-role/test-session',
        },
    }
    return mock_client


@pytest.fixture()
def mock_settings():
    with patch('backend.app.services.aws_client.settings') as mock_settings:
        # Ensure AWS_ROLE_ARN is None by default in tests
        mock_settings.AWS_ROLE_ARN = None
        mock_settings.AWS_REGION = 'us-east-1'
        mock_settings.AWS_PROFILE_NAME = 'default'
        yield mock_settings


def test_initialize_aws_client_service(mock_boto3, mock_settings):
    """Test initialization of AWSClientService with profile."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        service = AWSClientService(region_name='us-east-1', profile_name='test-profile')
        assert len(w) == 1
        assert issubclass(w[-1].category, DeprecationWarning)
        assert 'profile_name parameter is deprecated' in str(w[-1].message)

    mock_boto3.Session.assert_called_once_with(
        region_name='us-east-1',
    )
    assert service.region_name == 'us-east-1'
    assert service.profile_name == 'test-profile'
    assert service.session == mock_boto3.Session.return_value


def test_initialize_with_role_arn(mock_boto3, mock_sts_client):
    """Test initialization of AWSClientService with role ARN."""
    # Configure boto3 to return our mock STS client
    base_session = MagicMock()
    base_session.client.return_value = mock_sts_client
    mock_boto3.Session.side_effect = [base_session, MagicMock()]

    # Initialize with role ARN
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        service = AWSClientService(
            region_name='us-east-1',
            profile_name='test-profile',
            role_arn='arn:aws:iam::123456789012:role/test-role',
        )
        assert len(w) == 1
        assert issubclass(w[-1].category, DeprecationWarning)
        assert 'profile_name parameter is deprecated' in str(w[-1].message)

    # Verify the service was created correctly
    assert service.region_name == 'us-east-1'
    assert service.profile_name == 'test-profile'
    assert service.role_arn == 'arn:aws:iam::123456789012:role/test-role'

    # Check first session was created
    mock_boto3.Session.assert_any_call(
        region_name='us-east-1',
    )

    # Check STS client was used to assume role
    base_session.client.assert_called_once_with('sts')
    mock_sts_client.assume_role.assert_called_once()
    role_arn = mock_sts_client.assume_role.call_args.kwargs['RoleArn']
    assert role_arn == 'arn:aws:iam::123456789012:role/test-role'

    # Check second session was created with assumed role credentials
    mock_boto3.Session.assert_any_call(
        region_name='us-east-1',
        aws_access_key_id='test-access-key',
        aws_secret_access_key='test-secret-key',
        aws_session_token='test-session-token',
    )


def test_role_assumption_error(mock_boto3, mock_sts_client):
    """Test handling role assumption errors."""
    # Configure boto3 to return our mock STS client
    base_session = MagicMock()
    base_session.client.return_value = mock_sts_client
    mock_boto3.Session.return_value = base_session

    # Make STS client raise an error
    mock_sts_client.assume_role.side_effect = ClientError(
        {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
        'AssumeRole',
    )

    # Initialize with role ARN should raise ValueError
    with pytest.raises(ValueError, match='Role assumption error'):
        AWSClientService(
            region_name='us-east-1',
            role_arn='arn:aws:iam::123456789012:role/test-role',
        )


def test_get_client(mock_boto3, mock_settings):
    """Test get_client method."""
    service = AWSClientService(region_name='us-east-1')

    client = service.get_client('bedrock-runtime')

    service.session.client.assert_called_once_with(
        'bedrock-runtime',
        region_name='us-east-1',
    )
    assert client == service.session.client.return_value


@patch('backend.app.services.aws_client.boto3')
def test_handle_profile_not_found_error(mock_boto3):
    """Test handling ProfileNotFound error."""
    mock_boto3.Session.side_effect = ProfileNotFound(
        profile='test-profile',
    )

    with pytest.raises(ValueError, match='AWS configuration error'):
        AWSClientService(profile_name='test-profile')


@patch('backend.app.services.aws_client.boto3')
def test_handle_no_credentials_error(mock_boto3):
    """Test handling NoCredentialsError."""
    mock_boto3.Session.side_effect = NoCredentialsError()

    with pytest.raises(ValueError, match='AWS configuration error'):
        AWSClientService()


@patch('backend.app.services.aws_client.boto3')
def test_handle_no_region_error(mock_boto3):
    """Test handling NoRegionError."""
    mock_boto3.Session.side_effect = NoRegionError()

    with pytest.raises(ValueError, match='AWS configuration error'):
        AWSClientService()
