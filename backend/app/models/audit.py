import uuid
import hashlib
import json
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_email = Column(String(255), nullable=True)
    user_role = Column(String(100), nullable=True)
    
    action = Column(String(100), nullable=False)  # e.g. "AGENT_QUERY", "DOC_ACCESS", "POLICY_BLOCKED", "APPROVAL_RESOLVED"
    resource_type = Column(String(100), nullable=False)  # "DOCUMENT", "AGENT", "WORKFLOW", "USER"
    resource_id = Column(String(100), nullable=True)
    
    details = Column(JSON, default=dict)
    status = Column(String(50), default="SUCCESS")  # SUCCESS, BLOCKED, FAILED
    clearance_at_action = Column(String(50), nullable=True)
    ip_address = Column(String(50), default="127.0.0.1")
    integrity_hash = Column(String(64), nullable=True)  # SHA-256 tamper-evident hash
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    company = relationship("Company", back_populates="audit_logs")
    user = relationship("User")

    @staticmethod
    def calculate_hash(record_dict: dict) -> str:
        """Computes SHA-256 hash over canonical representation for tamper evidence."""
        sorted_bytes = json.dumps(record_dict, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(sorted_bytes).hexdigest()
