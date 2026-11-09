"""record embedding identity for immutable versions

Revision ID: e4a19d72b5c8
Revises: 9c1b2f0d4a21
Create Date: 2026-09-18
"""

from alembic import op
import sqlalchemy as sa


revision = "e4a19d72b5c8"
down_revision = "9c1b2f0d4a21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("document_versions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "embedding_model",
                sa.String(length=100),
                server_default="oraclex-deterministic-hash-v1",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column("embedding_dimensions", sa.Integer(), server_default="384", nullable=False)
        )


def downgrade() -> None:
    with op.batch_alter_table("document_versions") as batch_op:
        batch_op.drop_column("embedding_dimensions")
        batch_op.drop_column("embedding_model")
