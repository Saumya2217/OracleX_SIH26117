import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    department_id = Column(String, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    uploaded_by_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    title = Column(String(255), nullable=False)
    # Compatibility mirrors for the active version. New immutable metadata lives
    # on DocumentVersion and these fields are updated only when a version becomes ready.
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, default=0)
    content_sha256 = Column(String(64), nullable=True, index=True)

    clearance_level = Column(Integer, default=1)
    is_company_wide = Column(Boolean, default=False)
    tags = Column(JSON, default=list)
    summary = Column(Text, nullable=True)
    chunk_count = Column(Integer, default=0)
    status = Column(String(50), default="QUEUED", nullable=False)
    current_version_id = Column(
        String,
        ForeignKey("document_versions.id", name="fk_documents_current_version", use_alter=True, ondelete="SET NULL"),
        nullable=True,
    )
    version_count = Column(Integer, default=0, nullable=False)
    archived_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    company = relationship("Company", back_populates="documents")
    department = relationship("Department", back_populates="documents")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])
    versions = relationship(
        "DocumentVersion",
        back_populates="document",
        cascade="all, delete-orphan",
        foreign_keys="DocumentVersion.document_id",
        order_by="DocumentVersion.version_number",
    )
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_document_version_number"),
        UniqueConstraint("document_id", "content_sha256", name="uq_document_version_content"),
        Index("ix_document_versions_document_status", "document_id", "status"),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    created_by_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    version_number = Column(Integer, nullable=False)
    original_filename = Column(String(255), nullable=False)
    media_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    content_sha256 = Column(String(64), nullable=False)
    storage_key = Column(String(500), nullable=False)
    parser_version = Column(String(50), nullable=False, default="document-processor-v2")
    embedding_model = Column(String(100), nullable=False, default="oraclex-deterministic-hash-v1")
    embedding_dimensions = Column(Integer, nullable=False, default=384)
    status = Column(String(50), nullable=False, default="QUEUED")
    summary = Column(Text, nullable=True)
    chunk_count = Column(Integer, nullable=False, default=0)
    extraction_metadata = Column(JSON, default=dict)
    safe_error_message = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    ready_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)

    document = relationship("Document", back_populates="versions", foreign_keys=[document_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    chunks = relationship("DocumentChunk", back_populates="version", cascade="all, delete-orphan")
    jobs = relationship("IngestionJob", back_populates="version", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("version_id", "chunk_index", name="uq_version_chunk_index"),
        Index("ix_document_chunks_version_id", "version_id"),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    version_id = Column(String, ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    metadata_json = Column(JSON, default=dict)
    vector_id = Column(String(160), nullable=True, unique=True)
    created_at = Column(DateTime, default=utcnow)

    document = relationship("Document", back_populates="chunks")
    version = relationship("DocumentVersion", back_populates="chunks")


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    __table_args__ = (
        UniqueConstraint("version_id", "job_type", name="uq_ingestion_version_job_type"),
        Index("ix_ingestion_jobs_claim", "state", "available_at", "lease_expires_at"),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    version_id = Column(String, ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False)
    job_type = Column(String(50), nullable=False, default="INGEST_DOCUMENT")
    state = Column(String(50), nullable=False, default="QUEUED")
    attempt_count = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    lease_owner = Column(String(100), nullable=True)
    lease_expires_at = Column(DateTime, nullable=True)
    heartbeat_at = Column(DateTime, nullable=True)
    available_at = Column(DateTime, nullable=False, default=utcnow)
    error_code = Column(String(100), nullable=True)
    safe_error_message = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    version = relationship("DocumentVersion", back_populates="jobs")


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (Index("ix_outbox_events_claim", "state", "available_at", "lease_expires_at"),)

    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    aggregate_type = Column(String(50), nullable=False)
    aggregate_id = Column(String, nullable=False)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    state = Column(String(50), nullable=False, default="PENDING")
    attempt_count = Column(Integer, nullable=False, default=0)
    available_at = Column(DateTime, nullable=False, default=utcnow)
    lease_owner = Column(String(100), nullable=True)
    lease_expires_at = Column(DateTime, nullable=True)
    error_code = Column(String(100), nullable=True)
    safe_error_message = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    published_at = Column(DateTime, nullable=True)


class ServiceHeartbeat(Base):
    __tablename__ = "service_heartbeats"

    service_name = Column(String(100), primary_key=True)
    instance_id = Column(String(100), nullable=False)
    heartbeat_at = Column(DateTime, nullable=False, default=utcnow)
    details = Column(JSON, nullable=False, default=dict)
