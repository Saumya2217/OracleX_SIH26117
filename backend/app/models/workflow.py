import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, Boolean, JSON
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    department_id = Column(String, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    
    title = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False)  # e.g. "WF-ECN-01"
    description = Column(Text, nullable=True)
    category = Column(String(100), default="ENGINEERING")  # ENGINEERING, SAFETY, QUALITY, PURCHASE
    steps = Column(JSON, default=list)
    requires_approval = Column(Boolean, default=True)
    approval_role_code = Column(String(50), default="MANAGER")
    status = Column(String(50), default="ACTIVE")  # ACTIVE, DRAFT, ARCHIVED
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="workflows")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    department_id = Column(String, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    assigned_to_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    project_name = Column(String(150), default="General Operations")
    status = Column(String(50), default="TODO")  # TODO, IN_PROGRESS, REVIEW, COMPLETED
    priority = Column(String(50), default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    due_date = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="tasks")
    assigned_to = relationship("User", back_populates="tasks", foreign_keys=[assigned_to_id])
    created_by = relationship("User", foreign_keys=[created_by_id])


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    requester_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    approver_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    action_type = Column(String(100), nullable=False)  # e.g. "WORKFLOW_DEVIATION", "TOLERANCE_CHANGE", "SOP_UPDATE"
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    risk_level = Column(String(50), default="HIGH")  # LOW, MEDIUM, HIGH, CRITICAL
    payload = Column(JSON, default=dict)
    
    status = Column(String(50), default="PENDING")  # PENDING, APPROVED, REJECTED
    rationale = Column(Text, nullable=True)  # Filled by approver upon resolution
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company")
    requester = relationship("User", foreign_keys=[requester_id])
    approver = relationship("User", foreign_keys=[approver_id])
