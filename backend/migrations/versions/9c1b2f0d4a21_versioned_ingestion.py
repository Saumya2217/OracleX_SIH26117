"""versioned document ingestion

Revision ID: 9c1b2f0d4a21
Revises: 363fe407a3c9
Create Date: 2026-09-18
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from alembic import op
import sqlalchemy as sa


revision = "9c1b2f0d4a21"
down_revision = "363fe407a3c9"
branch_labels = None
depends_on = None


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def upgrade() -> None:
    op.create_table(
        "document_versions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("created_by_id", sa.String(), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("media_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("parser_version", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("extraction_metadata", sa.JSON(), nullable=True),
        sa.Column("safe_error_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("ready_at", sa.DateTime(), nullable=True),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "content_sha256", name="uq_document_version_content"),
        sa.UniqueConstraint("document_id", "version_number", name="uq_document_version_number"),
    )
    op.create_index(
        "ix_document_versions_document_status",
        "document_versions",
        ["document_id", "status"],
        unique=False,
    )

    with op.batch_alter_table("documents") as batch_op:
        batch_op.add_column(sa.Column("current_version_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("version_count", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("archived_at", sa.DateTime(), nullable=True))

    with op.batch_alter_table("document_chunks") as batch_op:
        batch_op.add_column(sa.Column("version_id", sa.String(), nullable=True))
        batch_op.alter_column(
            "vector_id",
            existing_type=sa.String(length=100),
            type_=sa.String(length=160),
            existing_nullable=True,
        )

    connection = op.get_bind()
    documents = connection.execute(
        sa.text(
            "SELECT id, uploaded_by_id, filename, file_type, file_path, file_size, "
            "content_sha256, summary, chunk_count, status, created_at FROM documents"
        )
    ).mappings()
    for document in documents:
        version_id = str(uuid.uuid4())
        document_status = document["status"] or "FAILED"
        version_status = "READY" if document_status == "INDEXED" else document_status
        digest = document["content_sha256"] or ("legacy-" + document["id"])[:64]
        created_at = document["created_at"] or utcnow()
        connection.execute(
            sa.text(
                "INSERT INTO document_versions "
                "(id, document_id, created_by_id, version_number, original_filename, media_type, "
                "file_size, content_sha256, storage_key, parser_version, status, summary, chunk_count, "
                "extraction_metadata, created_at, ready_at) "
                "VALUES (:id, :document_id, :created_by_id, 1, :filename, :media_type, :file_size, "
                ":digest, :storage_key, 'legacy-v1', :status, :summary, :chunk_count, :metadata, "
                ":created_at, :ready_at)"
            ),
            {
                "id": version_id,
                "document_id": document["id"],
                "created_by_id": document["uploaded_by_id"],
                "filename": document["filename"],
                "media_type": document["file_type"],
                "file_size": document["file_size"] or 0,
                "digest": digest,
                "storage_key": document["file_path"],
                "status": version_status,
                "summary": document["summary"],
                "chunk_count": document["chunk_count"] or 0,
                "metadata": "{}",
                "created_at": created_at,
                "ready_at": created_at if version_status == "READY" else None,
            },
        )
        connection.execute(
            sa.text(
                "UPDATE documents SET current_version_id = :version_id, version_count = 1, "
                "status = :status WHERE id = :document_id"
            ),
            {"version_id": version_id, "document_id": document["id"], "status": document_status},
        )
        connection.execute(
            sa.text("UPDATE document_chunks SET version_id = :version_id WHERE document_id = :document_id"),
            {"version_id": version_id, "document_id": document["id"]},
        )

    with op.batch_alter_table("documents") as batch_op:
        batch_op.create_foreign_key(
            "fk_documents_current_version",
            "document_versions",
            ["current_version_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.alter_column("status", existing_type=sa.String(length=50), nullable=False)

    with op.batch_alter_table("document_chunks") as batch_op:
        batch_op.create_foreign_key(
            "fk_document_chunks_version",
            "document_versions",
            ["version_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_unique_constraint("uq_version_chunk_index", ["version_id", "chunk_index"])
        batch_op.create_unique_constraint("uq_document_chunks_vector_id", ["vector_id"])
    op.create_index("ix_document_chunks_version_id", "document_chunks", ["version_id"], unique=False)

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("version_id", sa.String(), nullable=False),
        sa.Column("job_type", sa.String(length=50), nullable=False),
        sa.Column("state", sa.String(length=50), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("lease_owner", sa.String(length=100), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(), nullable=True),
        sa.Column("available_at", sa.DateTime(), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("safe_error_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["document_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version_id", "job_type", name="uq_ingestion_version_job_type"),
    )
    op.create_index(
        "ix_ingestion_jobs_claim",
        "ingestion_jobs",
        ["state", "available_at", "lease_expires_at"],
        unique=False,
    )

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("aggregate_type", sa.String(length=50), nullable=False),
        sa.Column("aggregate_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("state", sa.String(length=50), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(), nullable=False),
        sa.Column("lease_owner", sa.String(length=100), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("safe_error_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_outbox_events_claim",
        "outbox_events",
        ["state", "available_at", "lease_expires_at"],
        unique=False,
    )

    op.create_table(
        "service_heartbeats",
        sa.Column("service_name", sa.String(length=100), nullable=False),
        sa.Column("instance_id", sa.String(length=100), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("service_name"),
    )


def downgrade() -> None:
    op.drop_table("service_heartbeats")
    op.drop_index("ix_outbox_events_claim", table_name="outbox_events")
    op.drop_table("outbox_events")
    op.drop_index("ix_ingestion_jobs_claim", table_name="ingestion_jobs")
    op.drop_table("ingestion_jobs")

    op.drop_index("ix_document_chunks_version_id", table_name="document_chunks")
    with op.batch_alter_table("document_chunks") as batch_op:
        batch_op.drop_constraint("uq_document_chunks_vector_id", type_="unique")
        batch_op.drop_constraint("uq_version_chunk_index", type_="unique")
        batch_op.drop_constraint("fk_document_chunks_version", type_="foreignkey")
        batch_op.drop_column("version_id")
        batch_op.alter_column(
            "vector_id",
            existing_type=sa.String(length=160),
            type_=sa.String(length=100),
            existing_nullable=True,
        )

    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_constraint("fk_documents_current_version", type_="foreignkey")
        batch_op.drop_column("archived_at")
        batch_op.drop_column("version_count")
        batch_op.drop_column("current_version_id")
        batch_op.alter_column("status", existing_type=sa.String(length=50), nullable=True)

    op.drop_index("ix_document_versions_document_status", table_name="document_versions")
    op.drop_table("document_versions")
