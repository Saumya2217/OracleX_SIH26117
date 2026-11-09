from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class AdaptationProposalResponse(BaseModel):
    id: str
    company_id: str
    title: str
    category: str
    description: str
    detected_pattern: str
    proposed_adaptation: str
    projected_benefit: Optional[str] = None
    confidence_score: int
    status: str
    reviewed_by_id: Optional[str] = None
    review_notes: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ProposalReviewRequest(BaseModel):
    status: str  # "ACCEPTED", "REJECTED"
    review_notes: Optional[str] = None
