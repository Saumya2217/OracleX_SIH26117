import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(160), nullable=False)
    classification_level = Column(Integer, nullable=False, default=1)
    status = Column(String(30), nullable=False, default="ACTIVE")
    retention_until = Column(DateTime, nullable=True)
    next_sequence = Column(Integer, nullable=False, default=1)
    last_message_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", foreign_keys=[owner_id])
    messages = relationship(
        "ConversationMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.sequence",
    )
    runs = relationship("AgentRun", back_populates="conversation", cascade="all, delete-orphan")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    __table_args__ = (UniqueConstraint("conversation_id", "sequence", name="uq_conversation_message_sequence"),)

    id = Column(String, primary_key=True, default=generate_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = Column(String, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    author_user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    sequence = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")
    author = relationship("User", foreign_keys=[author_user_id])


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    requested_by_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    request_message_id = Column(String, ForeignKey("conversation_messages.id", ondelete="SET NULL"), nullable=True)
    response_message_id = Column(String, ForeignKey("conversation_messages.id", ondelete="SET NULL"), nullable=True, unique=True)
    status = Column(String(30), nullable=False, default="RUNNING")
    evidence_status = Column(String(40), nullable=True)
    generation_mode = Column(String(30), nullable=True)
    model_id = Column(String(120), nullable=True)
    prompt_version = Column(String(80), nullable=False, default="oraclex-agent-v1")
    retrieval_mode = Column(String(30), nullable=True)
    requires_review = Column(Boolean, nullable=False, default=False)
    business_request_id = Column(String, ForeignKey("business_requests.id", ondelete="SET NULL"), nullable=True)
    source_version_ids = Column(JSON, nullable=False, default=list)
    error_code = Column(String(80), nullable=True)
    safe_error_message = Column(String(500), nullable=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    conversation = relationship("Conversation", back_populates="runs")
    citations = relationship(
        "AgentRunCitation",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="AgentRunCitation.ordinal",
    )


class AgentRunCitation(Base):
    __tablename__ = "agent_run_citations"
    __table_args__ = (UniqueConstraint("run_id", "ordinal", name="uq_agent_run_citation_ordinal"),)

    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id = Column(String, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    ordinal = Column(Integer, nullable=False)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id = Column(String, ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id = Column(String, ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    page_number = Column(Integer, nullable=True)
    section_index = Column(Integer, nullable=True)
    sheet_name = Column(String(255), nullable=True)
    row_range = Column(String(100), nullable=True)
    source_type = Column(String(30), nullable=False)
    location_label = Column(String(255), nullable=False)
    excerpt = Column(Text, nullable=False)
    source_path = Column(String(500), nullable=False)

    run = relationship("AgentRun", back_populates="citations")
