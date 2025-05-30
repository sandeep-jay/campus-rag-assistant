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
from datetime import datetime, timedelta

from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend.app.core.config_manager import settings
from backend.app.db.database import get_db
from backend.app.services.db import DatabaseService

logger = logging.getLogger('app.core.security')

# OAuth2 token URL and scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f'{settings.API_V1_STR}/auth/token', auto_error=False)


async def get_token_from_request(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    access_token: str | None = Cookie(None, alias='access_token'),
) -> str | None:
    # Extract token from either authorization header or cookie.
    logger.info(f'Extracting token - Bearer: {bool(token)}, Cookie: {bool(access_token)}')

    # Return the first available token
    if token:
        logger.info('Using bearer token from authorization header')
        return token
    elif access_token:
        logger.info('Using access_token from cookie')
        return access_token

    logger.warning('No token found in request')
    return None


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    # Create a JWT access token.
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        )

    to_encode.update({'exp': expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str) -> dict | None:
    # Verify a JWT token and return its payload if valid.
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.ExpiredSignatureError:
        # Add specific handling for expired tokens
        return None
    except jwt.JWTClaimsError:
        # Add specific handling for invalid claims
        return None
    except JWTError:
        # General JWT error
        return None
    except ValueError:
        # Handle invalid token format
        return None
    except Exception as e:
        # Log unexpected exceptions but don't expose details
        logger.exception(f'Unexpected error verifying token: {e!s}')
        return None


async def get_current_user(
    token: str | None = Depends(get_token_from_request),
    db: Session = Depends(get_db),
):
    # Get the current user from token (either bearer or cookie).
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )

    expired_token_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Token has expired',
        headers={'WWW-Authenticate': 'Bearer'},
    )

    if not token:
        logger.error('No token found in request')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Not authenticated',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    try:
        logger.info(f'Verifying token (length: {len(token)})')
        payload = verify_token(token)
        if payload is None:
            logger.error('Token verification failed')
            raise credentials_exception

        logger.info(f'Token payload: {payload}')
        username: str = payload.get('sub')
        if username is None:
            logger.error("No 'sub' claim in token")
            raise credentials_exception
    except jwt.ExpiredSignatureError as e:
        logger.error(f'Token expired: {e}')
        raise expired_token_exception
    except JWTError as e:
        logger.error(f'JWT error: {e}')
        raise credentials_exception
    except ValueError as e:
        logger.error(f'Value error: {e}')
        raise credentials_exception
    except Exception as e:
        logger.exception(f'Unexpected error in get_current_user: {e}')
        raise credentials_exception

    logger.info(f'Looking up user: {username}')
    db_service = DatabaseService(db)
    user = db_service.get_user_by_username(username)
    if user is None:
        logger.error(f'User not found: {username}')
        raise credentials_exception

    logger.info(f'Authentication successful for user: {username}')
    return user


async def get_current_user_from_cookie(
    access_token: str | None = Cookie(None, alias='access_token'),
    db: Session = Depends(get_db),
):
    # Get the current user from the cookie only.
    if not access_token:
        logger.error('No cookie token found')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Not authenticated',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    try:
        logger.info(f'Verifying cookie token (length: {len(access_token)})')
        payload = verify_token(access_token)
        if payload is None:
            logger.error('Cookie token verification failed')
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid or expired token',
            )

        logger.info(f'Cookie token payload: {payload}')
        username: str = payload.get('sub')
        if username is None:
            logger.error("No 'sub' claim in cookie token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid token payload',
            )
    except Exception as e:
        logger.exception(f'Error in get_current_user_from_cookie: {e}')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Could not validate credentials',
        )

    logger.info(f'Looking up user from cookie: {username}')
    db_service = DatabaseService(db)
    user = db_service.get_user_by_username(username)
    if user is None:
        logger.error(f'User not found from cookie: {username}')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='User not found',
        )

    logger.info(f'Cookie authentication successful for user: {username}')
    return user
