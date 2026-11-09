import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, JSON
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class AdaptationProposal(Base):
    __tablename__ = "adaptation_proposals"

    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    
    title = Column(String(255), nullable=False)
    category = Column(String(100), default="WORKFLOW_OPTIMIZATION")  # BOTTLENECK, WORKFLOW_OPTIMIZATION, COMPLIANCE_GAP, TASK_REALLOCATION
    description = Column(Text, nullable=False)
    detected_pattern = Column(Text, nullable=False)
    proposed_adaptation = Column(Text, nullable=False)
    projected_benefit = Column(Text, nullable=True)
    confidence_score = Column(Integer, default=85)  # 0 to 100
    
    status = Column(String(50), default="PROPOSED")  # PROPOSED, ACCEPTED, REJECTED, ARCHIVED
    reviewed_by_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)

    company = relationship("Company")
    reviewed_by = relationship("User")


class FeedbackRecord(Base):
    __tablename__ = "feedback_records"

    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    query_text = Column(Text, nullable=False)
    agent_response = Column(Text, nullable=False)
    rating = Column(Integer, nullable=False)  # 1 (positive) or -1 (negative)
    correction = Column(Text, nullable=True)
    category = Column(String(100), default="ACCURACY")
    
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company")
    user = relationship("User")
