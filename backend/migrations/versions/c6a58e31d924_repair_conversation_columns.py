"""repair conversation columns in databases stamped with an earlier M06 revision

Revision ID: c6a58e31d924
Revises: b7d2c4e91f60
Create Date: 2026-10-12
"""

from alembic import op
import sqlalchemy as sa


revision = "c6a58e31d924"
down_revision = "b7d2c4e91f60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    existing = {column["name"] for column in sa.inspect(connection).get_columns("conversations")}
    if "retention_until" not in existing:
        op.add_column("conversations", sa.Column("retention_until", sa.DateTime(), nullable=True))
    if "next_sequence" not in existing:
        op.add_column("conversations", sa.Column("next_sequence", sa.Integer(), nullable=True))
        connection.execute(sa.text(
            "UPDATE conversations SET next_sequence = COALESCE(("
            "SELECT MAX(sequence) + 1 FROM conversation_messages "
            "WHERE conversation_messages.conversation_id = conversations.id), 1)"
        ))
        with op.batch_alter_table("conversations") as batch:
            batch.alter_column("next_sequence", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    # The preceding M06 schema defines both columns. Preserve them on downgrade.
    pass
