"""Create LangGraph helpdesk checkpoint tables.

Revision ID: 0004
Revises: 0003

The application must not call ``AsyncPostgresSaver.setup()`` at startup.
LangGraph checkpoint schema changes are owned by Alembic revisions so deploys
are explicit, reviewable, and rollbackable.
"""

from alembic import op

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS checkpoint_migrations (
            v INTEGER PRIMARY KEY
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS checkpoints (
            thread_id TEXT NOT NULL,
            checkpoint_ns TEXT NOT NULL DEFAULT '',
            checkpoint_id TEXT NOT NULL,
            parent_checkpoint_id TEXT,
            type TEXT,
            checkpoint JSONB NOT NULL,
            metadata JSONB NOT NULL DEFAULT '{}',
            PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS checkpoint_blobs (
            thread_id TEXT NOT NULL,
            checkpoint_ns TEXT NOT NULL DEFAULT '',
            channel TEXT NOT NULL,
            version TEXT NOT NULL,
            type TEXT NOT NULL,
            blob BYTEA,
            PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS checkpoint_writes (
            thread_id TEXT NOT NULL,
            checkpoint_ns TEXT NOT NULL DEFAULT '',
            checkpoint_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            idx INTEGER NOT NULL,
            channel TEXT NOT NULL,
            type TEXT,
            blob BYTEA NOT NULL,
            PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
        )
        """
    )
    op.execute(
        """
        INSERT INTO checkpoint_migrations (v)
        VALUES (0), (1), (2), (3), (4), (5), (6), (7), (8)
        ON CONFLICT (v) DO NOTHING
        """
    )

    with op.get_context().autocommit_block():
        op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS checkpoints_thread_id_idx ON checkpoints(thread_id)')
        op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS checkpoint_blobs_thread_id_idx ON checkpoint_blobs(thread_id)')
        op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS checkpoint_writes_thread_id_idx ON checkpoint_writes(thread_id)')


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute('DROP INDEX CONCURRENTLY IF EXISTS checkpoint_writes_thread_id_idx')
        op.execute('DROP INDEX CONCURRENTLY IF EXISTS checkpoint_blobs_thread_id_idx')
        op.execute('DROP INDEX CONCURRENTLY IF EXISTS checkpoints_thread_id_idx')

    op.execute('DROP TABLE IF EXISTS checkpoint_writes')
    op.execute('DROP TABLE IF EXISTS checkpoint_blobs')
    op.execute('DROP TABLE IF EXISTS checkpoints')
    op.execute('DROP TABLE IF EXISTS checkpoint_migrations')
