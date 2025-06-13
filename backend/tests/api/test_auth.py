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

from fastapi import status
from starlette.testclient import TestClient


def test_register(client: TestClient) -> None:
    response = client.post(
        '/api/auth/register',
        json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpassword123',
        },
    )
    assert response.status_code == status.HTTP_200_OK
    assert 'message' in response.json()


def test_register_duplicate_username(
    client: TestClient,
    test_user: dict[str, str],
) -> None:
    # First register a user
    response = client.post('/api/auth/register', json=test_user)
    assert response.status_code == status.HTTP_200_OK

    # Try to register with the same username but different email
    response = client.post(
        '/api/auth/register',
        json={
            'username': test_user['username'],
            'email': 'different@example.com',
            'password': 'testpassword123',
        },
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'Username already registered' in response.json()['detail']


def test_register_duplicate_email(
    client: TestClient,
    test_user: dict[str, str],
) -> None:
    # First register a user
    response = client.post('/api/auth/register', json=test_user)
    assert response.status_code == status.HTTP_200_OK

    # Try to register with the same email but different username
    response = client.post(
        '/api/auth/register',
        json={
            'username': 'newuser',
            'email': test_user['email'],
            'password': 'testpassword123',
        },
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'Email already registered' in response.json()['detail']


def test_login(client: TestClient, test_user: dict[str, str]) -> None:
    # Register user first
    response = client.post('/api/auth/register', json=test_user)
    assert response.status_code == status.HTTP_200_OK

    # Try to login
    response = client.post(
        '/api/auth/token',
        data={'username': test_user['username'], 'password': test_user['password']},
    )
    assert response.status_code == status.HTTP_200_OK
    assert 'access_token' in response.json()
    assert 'token_type' in response.json()
    assert response.json()['token_type'] == 'bearer'


def test_login_wrong_password(client: TestClient, test_user: dict[str, str]) -> None:
    # Register user first
    response = client.post('/api/auth/register', json=test_user)
    assert response.status_code == status.HTTP_200_OK

    # Try to login with wrong password
    response = client.post(
        '/api/auth/token',
        data={'username': test_user['username'], 'password': 'wrongpassword'},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert 'Incorrect username or password' in response.json()['detail']
