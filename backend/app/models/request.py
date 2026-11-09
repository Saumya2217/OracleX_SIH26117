import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class BusinessRequest(Base):
    __tablename__ = "business_requests"

    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    requester_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_reviewer_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    request_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    risk_level = Column(String(30), nullable=False, default="MEDIUM")
    status = Column(String(30), nullable=False, default="DRAFT", index=True)
    lock_version = Column(Integer, nullable=False, default=1)
    current_version_id = Column(String, nullable=False)
    submitted_version_id = Column(String, nullable=True)
    source_context = Column(JSON, nullable=False, default=dict)
    submitted_at = Column(DateTime, nullable=True)
    decision = Column(String(30), nullable=True)
    decision_reason = Column(Text, nullable=True)
    decided_by_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decided_at = Column(DateTime, nullable=True)
    fulfilled_by_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    fulfillment_notes = Column(Text, nullable=True)
    fulfilled_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    requester = relationship("User", foreign_keys=[requester_id])
    assigned_reviewer = relationship("User", foreign_keys=[assigned_reviewer_id])
    decided_by = relationship("User", foreign_keys=[decided_by_id])
    fulfilled_by = relationship("User", foreign_keys=[fulfilled_by_id])
    versions = relationship(
        "BusinessRequestVersion",
        back_populates="request",
        cascade="all, delete-orphan",
        order_by="BusinessRequestVersion.version_number",
    )
    events = relationship(
        "BusinessRequestEvent",
        back_populates="request",
        cascade="all, delete-orphan",
        order_by="BusinessRequestEvent.created_at",
    )


class BusinessRequestVersion(Base):
    __tablename__ = "business_request_versions"
    __table_args__ = (UniqueConstraint("request_id", "version_number", name="uq_business_request_version_number"),)

    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    request_id = Column(String, ForeignKey("business_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    payload = Column(JSON, nullable=False)
    created_by_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    request = relationship("BusinessRequest", back_populates="versions")
    created_by = relationship("User", foreign_keys=[created_by_id])


class BusinessRequestEvent(Base):
    __tablename__ = "business_request_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    request_id = Column(String, ForeignKey("business_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    event_type = Column(String(50), nullable=False)
    from_status = Column(String(30), nullable=True)
    to_status = Column(String(30), nullable=False)
    reason = Column(Text, nullable=True)
    event_metadata = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    request = relationship("BusinessRequest", back_populates="events")
    actor = relationship("User", foreign_keys=[actor_id])


class InternalNotification(Base):
    __tablename__ = "internal_notifications"

    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    request_id = Column(String, ForeignKey("business_requests.id", ondelete="CASCADE"), nullable=True)
    notification_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    deep_link = Column(String(500), nullable=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    recipient = relationship("User", foreign_keys=[recipient_id])
