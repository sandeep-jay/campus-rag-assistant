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

from sqlalchemy.orm import Session

from backend.app.core.logger import logger
from backend.app.core.password import get_password_hash
from backend.app.models.tenant import Tenant
from backend.app.models.user import User


class DatabaseService:
    def __init__(self, db: Session):
        self.db = db
        logger.debug('DatabaseService initialized')

    # Tenant methods
    def create_tenant(self, name: str, description: str | None = None) -> Tenant:
        logger.info(f'Creating new tenant: {name}')
        db_tenant = Tenant(name=name, description=description)
        self.db.add(db_tenant)
        self.db.commit()
        self.db.refresh(db_tenant)
        logger.info(f'Tenant created with ID: {db_tenant.id}')
        return db_tenant

    def get_tenant(self, tenant_id: int) -> Tenant | None:
        logger.debug(f'Getting tenant with ID: {tenant_id}')
        return self.db.query(Tenant).filter(Tenant.id == tenant_id).first()

    def get_tenant_by_name(self, name: str) -> Tenant | None:
        logger.debug(f'Getting tenant by name: {name}')
        return self.db.query(Tenant).filter(Tenant.name == name).first()

    def get_tenants(self, skip: int = 0, limit: int = 100) -> list[Tenant]:
        logger.debug(f'Getting tenants (skip={skip}, limit={limit})')
        return self.db.query(Tenant).offset(skip).limit(limit).all()

    # User methods
    def get_user(self, user_id: int) -> User | None:
        logger.debug(f'Getting user with ID: {user_id}')
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_email(self, email: str) -> User | None:
        logger.debug(f'Getting user by email: {email}')
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_username(self, username: str) -> User | None:
        logger.debug(f'Getting user by username: {username}')
        return self.db.query(User).filter(User.username == username).first()

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        tenant_id: int | None = None,
    ) -> User:
        logger.info(f'Creating new user: {username} (email: {email})')
        hashed_password = get_password_hash(password)
        db_user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            tenant_id=tenant_id,
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        logger.info(f'User created with ID: {db_user.id}')
        return db_user

    def get_users(
        self,
        skip: int = 0,
        limit: int = 100,
        tenant_id: int | None = None,
    ) -> list[User]:
        logger.debug(
            f'Getting users (skip={skip}, limit={limit}, tenant_id={tenant_id})',
        )
        query = self.db.query(User)
        if tenant_id is not None:
            query = query.filter(User.tenant_id == tenant_id)
        return query.offset(skip).limit(limit).all()

    def authenticate_user(self, username: str, password: str) -> User | None:
        logger.info(f'Authenticating user: {username}')
        # Use a single query with OR condition to check both username and email
        user = (
            self.db.query(User)
            .filter(
                (User.username == username) | (User.email == username),
            )
            .first()
        )

        if not user or not user.verify_password(password):
            logger.warning(f'Authentication failed for user: {username}')
            return None

        logger.info(f'Authentication successful for user: {username}')
        return user
