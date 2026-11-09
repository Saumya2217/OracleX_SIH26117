"""persistent conversations and accountable requests

Revision ID: b7d2c4e91f60
Revises: e4a19d72b5c8
Create Date: 2026-09-19
"""

from alembic import op
import sqlalchemy as sa


revision = "b7d2c4e91f60"
down_revision = "e4a19d72b5c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "business_requests",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("requester_id", sa.String(), nullable=False),
        sa.Column("assigned_reviewer_id", sa.String(), nullable=True),
        sa.Column("request_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("lock_version", sa.Integer(), nullable=False),
        sa.Column("current_version_id", sa.String(), nullable=False),
        sa.Column("submitted_version_id", sa.String(), nullable=True),
        sa.Column("source_context", sa.JSON(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("decision", sa.String(length=30), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("decided_by_id", sa.String(), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("fulfilled_by_id", sa.String(), nullable=True),
        sa.Column("fulfillment_notes", sa.Text(), nullable=True),
        sa.Column("fulfilled_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_reviewer_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["decided_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["fulfilled_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_business_requests_company_id", "business_requests", ["company_id"])
    op.create_index("ix_business_requests_requester_id", "business_requests", ["requester_id"])
    op.create_index("ix_business_requests_assigned_reviewer_id", "business_requests", ["assigned_reviewer_id"])
    op.create_index("ix_business_requests_status", "business_requests", ["status"])

    op.create_table(
        "business_request_versions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("request_id", sa.String(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_by_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["request_id"], ["business_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", "version_number", name="uq_business_request_version_number"),
    )
    op.create_index("ix_business_request_versions_company_id", "business_request_versions", ["company_id"])
    op.create_index("ix_business_request_versions_request_id", "business_request_versions", ["request_id"])

    op.create_table(
        "business_request_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("request_id", sa.String(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("from_status", sa.String(length=30), nullable=True),
        sa.Column("to_status", sa.String(length=30), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("event_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["request_id"], ["business_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_business_request_events_company_id", "business_request_events", ["company_id"])
    op.create_index("ix_business_request_events_request_id", "business_request_events", ["request_id"])

    op.create_table(
        "internal_notifications",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("recipient_id", sa.String(), nullable=False),
        sa.Column("request_id", sa.String(), nullable=True),
        sa.Column("notification_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("deep_link", sa.String(length=500), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["request_id"], ["business_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_internal_notifications_company_id", "internal_notifications", ["company_id"])
    op.create_index("ix_internal_notifications_recipient_id", "internal_notifications", ["recipient_id"])

    op.create_table(
        "conversations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("owner_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("classification_level", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("retention_until", sa.DateTime(), nullable=True),
        sa.Column("next_sequence", sa.Integer(), nullable=False),
        sa.Column("last_message_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversations_company_id", "conversations", ["company_id"])
    op.create_index("ix_conversations_owner_id", "conversations", ["owner_id"])

    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("conversation_id", sa.String(), nullable=False),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("author_user_id", sa.String(), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("conversation_id", "sequence", name="uq_conversation_message_sequence"),
    )
    op.create_index("ix_conversation_messages_conversation_id", "conversation_messages", ["conversation_id"])
    op.create_index("ix_conversation_messages_company_id", "conversation_messages", ["company_id"])

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("conversation_id", sa.String(), nullable=False),
        sa.Column("requested_by_id", sa.String(), nullable=True),
        sa.Column("request_message_id", sa.String(), nullable=True),
        sa.Column("response_message_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("evidence_status", sa.String(length=40), nullable=True),
        sa.Column("generation_mode", sa.String(length=30), nullable=True),
        sa.Column("model_id", sa.String(length=120), nullable=True),
        sa.Column("prompt_version", sa.String(length=80), nullable=False),
        sa.Column("retrieval_mode", sa.String(length=30), nullable=True),
        sa.Column("requires_review", sa.Boolean(), nullable=False),
        sa.Column("business_request_id", sa.String(), nullable=True),
        sa.Column("source_version_ids", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("safe_error_message", sa.String(length=500), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["request_message_id"], ["conversation_messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["response_message_id"], ["conversation_messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["business_request_id"], ["business_requests.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("response_message_id"),
    )
    op.create_index("ix_agent_runs_company_id", "agent_runs", ["company_id"])
    op.create_index("ix_agent_runs_conversation_id", "agent_runs", ["conversation_id"])

    op.create_table(
        "agent_run_citations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("company_id", sa.String(), nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("version_id", sa.String(), nullable=False),
        sa.Column("chunk_id", sa.String(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section_index", sa.Integer(), nullable=True),
        sa.Column("sheet_name", sa.String(length=255), nullable=True),
        sa.Column("row_range", sa.String(length=100), nullable=True),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("location_label", sa.String(length=255), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("source_path", sa.String(length=500), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["document_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "ordinal", name="uq_agent_run_citation_ordinal"),
    )
    op.create_index("ix_agent_run_citations_company_id", "agent_run_citations", ["company_id"])
    op.create_index("ix_agent_run_citations_run_id", "agent_run_citations", ["run_id"])
    op.create_index("ix_agent_run_citations_document_id", "agent_run_citations", ["document_id"])
    op.create_index("ix_agent_run_citations_version_id", "agent_run_citations", ["version_id"])


def downgrade() -> None:
    op.drop_table("agent_run_citations")
    op.drop_table("agent_runs")
    op.drop_table("conversation_messages")
    op.drop_table("conversations")
    op.drop_table("internal_notifications")
    op.drop_table("business_request_events")
    op.drop_table("business_request_versions")
    op.drop_table("business_requests")
