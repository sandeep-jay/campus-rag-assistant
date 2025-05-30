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
from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.app.core.config_manager import settings
from backend.app.core.security import create_access_token, get_current_user, verify_token
from backend.app.db.database import get_db
from backend.app.models.user import User
from backend.app.schemas.user import UserCreate, UserLogin
from backend.app.services.db import DatabaseService

router = APIRouter()


@router.post('/register')
async def register(
    user: UserCreate,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    db_service = DatabaseService(db)

    # Check for existing username or email in a single transaction
    existing_user = (
        db_service.db.query(User)
        .filter(
            (User.username == user.username) | (User.email == user.email),
        )
        .first()
    )

    if existing_user:
        if existing_user.username == user.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Username already registered',
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Email already registered',
            )

    # Create new user
    db_service.create_user(user.username, user.email, user.password)
    return {'message': 'User registered successfully'}


@router.post('/token')
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    # Traditional token-based login for backward compatibility.
    db_service = DatabaseService(db)
    user = db_service.authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect username or password',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={'sub': user.username},
        expires_delta=access_token_expires,
    )
    return {
        'access_token': access_token,
        'token_type': 'bearer',
        'user_id': user.id,
        'username': user.username,
        'expires_in': settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Return expiry in seconds
    }


@router.post('/login')
async def login_with_cookie(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    # Cookie-based login that sets HTTP-only cookie.
    db_service = DatabaseService(db)
    user = db_service.authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect username or password',
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={'sub': user.username},
        expires_delta=access_token_expires,
    )

    # Set cookie
    response.set_cookie(
        key='access_token',
        value=access_token,
        httponly=True,
        secure=False,  # Set to False for local development without HTTPS
        samesite='lax',
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path='/',
    )

    return {
        'user_id': user.id,
        'username': user.username,
        'status': 'success',
    }


@router.post('/login-json')
async def login_with_json(
    user_data: UserLogin,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    # JSON-based login that sets HTTP-only cookie.
    logger = logging.getLogger('app.api.auth')
    logger.info(f'Attempting JSON login for user: {user_data.username}')

    db_service = DatabaseService(db)
    user = db_service.authenticate_user(user_data.username, user_data.password)

    if not user:
        logger.warning(f'Failed login attempt for user: {user_data.username}')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect username or password',
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={'sub': user.username},
        expires_delta=access_token_expires,
    )

    # Set cookie
    response.set_cookie(
        key='access_token',
        value=access_token,
        httponly=True,
        secure=False,  # Set to False for local development without HTTPS
        samesite='lax',
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path='/',
        domain=None,
    )

    logger.info(f'Successful JSON login for user: {user_data.username}')
    return {
        'user_id': user.id,
        'username': user.username,
        'status': 'success',
    }


@router.post('/logout')
async def logout(response: Response) -> dict[str, Any]:
    """Clear the authentication cookie."""
    response.delete_cookie(
        key='access_token',
        path='/',
        httponly=True,
        secure=False,
        samesite='lax',
    )
    return {'status': 'success'}


@router.get('/me')
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)],
    access_token: str | None = Cookie(None, alias='access_token'),
) -> dict[str, Any]:
    """Get the current user's information using either token auth or cookie auth."""
    return {
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
    }


@router.get('/debug-auth')
async def debug_auth(
    access_token: str | None = Cookie(None, alias='access_token'),
    auth_header: str | None = None,
) -> dict[str, Any]:
    # Debug authentication for testing.
    logger = logging.getLogger('app.api.auth')

    result = {
        'cookie_present': access_token is not None,
        'cookie_length': len(access_token) if access_token else 0,
        'auth_header_present': auth_header is not None,
    }

    # Try to decode the token
    if access_token:
        try:
            payload = verify_token(access_token)
            result['token_valid'] = payload is not None
            result['token_payload'] = payload
            logger.info(f'Debug token payload: {payload}')
        except Exception as e:
            result['token_valid'] = False
            result['token_error'] = str(e)
            logger.error(f'Debug token error: {e}')

    return result
