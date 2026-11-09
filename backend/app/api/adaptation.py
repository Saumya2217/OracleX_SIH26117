from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.company import User
from app.models.adaptation import AdaptationProposal
from app.schemas.adaptation import AdaptationProposalResponse, ProposalReviewRequest
from app.api.deps import get_current_user
from app.services.audit_service import record_audit_event

router = APIRouter(prefix="/adaptation", tags=["Continuous Adaptation & Learning (Levels 3 & 4)"])

@router.get("/proposals", response_model=List[AdaptationProposalResponse])
def list_adaptation_proposals(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Level 3: Lists AI-detected patterns and reviewable organizational adaptation proposals."""
    query = db.query(AdaptationProposal).filter(AdaptationProposal.company_id == current_user.company_id)
    if status:
        query = query.filter(AdaptationProposal.status == status)
    
    proposals = query.order_by(AdaptationProposal.created_at.desc()).all()
    return [AdaptationProposalResponse.model_validate(p) for p in proposals]

@router.post("/proposals/{proposal_id}/review", response_model=AdaptationProposalResponse)
def review_proposal(
    proposal_id: str,
    review: ProposalReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Level 4: Governed institutional learning.
    Managers or Executives can accept or reject adaptation proposals.
    OracleX guarantees that no uncontrolled autonomous policy changes take place.
    """
    if (current_user.clearance_level or 1) < 3 and not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized: Proposal review requires Manager or Executive clearance (Level 3+)."
        )

    proposal = db.query(AdaptationProposal).filter(
        AdaptationProposal.id == proposal_id,
        AdaptationProposal.company_id == current_user.company_id
    ).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found.")

    proposal.status = review.status.upper()
    proposal.reviewed_by_id = current_user.id
    proposal.review_notes = review.review_notes
    proposal.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(proposal)

    # Audit the governed self-improvement decision
    record_audit_event(
        db=db,
        company_id=current_user.company_id,
        action=f"ADAPTATION_{proposal.status}",
        resource_type="ADAPTATION_PROPOSAL",
        resource_id=proposal.id,
        user=current_user,
        details={
            "title": proposal.title,
            "status": proposal.status,
            "notes": review.review_notes
        }
    )

    return AdaptationProposalResponse.model_validate(proposal)
