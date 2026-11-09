from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.assistant import Conversation
from app.models.company import User
from app.schemas.conversation import ConversationDetailResponse, ConversationSummaryResponse, ConversationUpdateRequest
from app.services.conversation_service import conversation_detail, conversation_summary


router = APIRouter(prefix="/conversations", tags=["Assistant conversations"])


def owned_conversation(db: Session, user: User, conversation_id: str) -> Conversation:
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.company_id == user.company_id,
        Conversation.owner_id == user.id,
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conversation


@router.get("", response_model=list[ConversationSummaryResponse])
def list_conversations(
    include_archived: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Conversation).filter(
        Conversation.company_id == current_user.company_id,
        Conversation.owner_id == current_user.id,
    )
    if not include_archived:
        query = query.filter(Conversation.status == "ACTIVE")
    return [conversation_summary(item) for item in query.order_by(Conversation.last_message_at.desc()).limit(100).all()]


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return conversation_detail(db, owned_conversation(db, current_user, conversation_id), current_user)


@router.patch("/{conversation_id}", response_model=ConversationSummaryResponse)
def update_conversation(
    conversation_id: str,
    payload: ConversationUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = owned_conversation(db, current_user, conversation_id)
    if payload.title is not None:
        conversation.title = payload.title.strip()
    if payload.status is not None:
        conversation.status = payload.status
    db.commit()
    db.refresh(conversation)
    return conversation_summary(conversation)
