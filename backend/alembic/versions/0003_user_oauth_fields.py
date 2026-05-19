"""Add OAuth identity fields on user.

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('user', 'hashed_password', existing_type=sa.String(), nullable=True)
    op.add_column(
        'user',
        sa.Column('auth_provider', sa.String(), nullable=False, server_default='local'),
    )
    op.add_column(
        'user',
        sa.Column('provider_subject', sa.String(), nullable=True),
    )
    op.create_index('ix_user_auth_provider', 'user', ['auth_provider'], unique=False)
    op.create_index(
        'uq_user_oauth_identity',
        'user',
        ['auth_provider', 'provider_subject'],
        unique=True,
        postgresql_where=sa.text('provider_subject IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index('uq_user_oauth_identity', table_name='user')
    op.drop_index('ix_user_auth_provider', table_name='user')
    op.drop_column('user', 'provider_subject')
    op.drop_column('user', 'auth_provider')
    op.alter_column('user', 'hashed_password', existing_type=sa.String(), nullable=False)
