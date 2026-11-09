from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.company import User
from app.models.assistant import AgentRun, AgentRunCitation, Conversation, ConversationMessage
from app.models.knowledge import Document
from app.models.adaptation import FeedbackRecord
from app.schemas.agent import AgentHealthResponse, AgentQueryRequest, AgentQueryResponse, FeedbackSubmitRequest, FeedbackSubmitResponse
from app.api.deps import get_current_user
from app.agents.orchestrator import AIOrchestrator
from app.agents.llm_client import llm_client
from app.config import settings

PROMPT_VERSION = "oraclex-agent-v1"

router = APIRouter(prefix="/agents", tags=["Agentic AI Workbench"])

@router.post("/query", response_model=AgentQueryResponse)
async def query_agent_workbench(
    request: AgentQueryRequest,
    fastapi_req: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submits a query to the sovereign multi-agent pipeline:
    Company Context -> Intent Routing -> Specialized Agent -> Guardrail Verification -> Gating -> Audit Log.
    """
    client_ip = fastapi_req.client.host if fastapi_req.client else "127.0.0.1"
    if request.conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == request.conversation_id,
            Conversation.company_id == current_user.company_id,
            Conversation.owner_id == current_user.id,
        ).with_for_update().first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        if conversation.status != "ACTIVE":
            raise HTTPException(status_code=409, detail="Archived conversations cannot receive new messages.")
        previous_questions = [
            message.content
            for message in conversation.messages
            if message.role == "USER"
        ][-2:]
        user_sequence = conversation.next_sequence
        assistant_sequence = user_sequence + 1
        conversation.next_sequence += 2
    else:
        previous_questions = []
        title = " ".join(request.message.strip().split())[:157]
        conversation = Conversation(
            company_id=current_user.company_id,
            owner_id=current_user.id,
            title=title + ("…" if len(request.message.strip()) > 157 else ""),
            classification_level=1,
            status="ACTIVE",
            next_sequence=3,
        )
        db.add(conversation)
        db.flush()
        user_sequence = 1
        assistant_sequence = 2
    user_message = ConversationMessage(
        conversation_id=conversation.id,
        company_id=current_user.company_id,
        author_user_id=current_user.id,
        role="USER",
        content=request.message,
        sequence=user_sequence,
    )
    run = AgentRun(
        company_id=current_user.company_id,
        conversation_id=conversation.id,
        requested_by_id=current_user.id,
        status="RUNNING",
        model_id=settings.OLLAMA_DEFAULT_MODEL,
        prompt_version=PROMPT_VERSION,
        retrieval_mode="none",
        started_at=datetime.utcnow(),
    )
    db.add_all([user_message, run])
    db.flush()
    run.request_message_id = user_message.id
    conversation.last_message_at = user_message.created_at
    db.commit()

    try:
        response = await AIOrchestrator.process_query(
            db=db,
            user=current_user,
            query=request.message,
            conversation_id=conversation.id,
            image_base64=request.image_base64,
            ip_address=client_ip,
            previous_questions=previous_questions,
        )
    except Exception as exc:
        db.rollback()
        run = db.get(AgentRun, run.id)
        conversation = db.get(Conversation, conversation.id)
        failure_message = ConversationMessage(
            conversation_id=conversation.id,
            company_id=current_user.company_id,
            role="ASSISTANT",
            content="OracleX could not complete this request. The failed run was saved; retry when the local service is available.",
            sequence=assistant_sequence,
        )
        db.add(failure_message)
        db.flush()
        run.response_message_id = failure_message.id
        run.status = "FAILED"
        run.generation_mode = "NONE"
        run.error_code = "ASSISTANT_RUN_FAILED"
        run.safe_error_message = "The assistant run failed before an answer was completed."
        run.completed_at = datetime.utcnow()
        conversation.last_message_at = failure_message.created_at
        db.commit()
        raise HTTPException(status_code=503, detail="The assistant run failed and was saved for review.") from exc

    assistant_message = ConversationMessage(
        conversation_id=conversation.id,
        company_id=current_user.company_id,
        role="ASSISTANT",
        content=response.answer,
        sequence=assistant_sequence,
    )
    db.add(assistant_message)
    db.flush()
    run = db.get(AgentRun, run.id)
    run.response_message_id = assistant_message.id
    run.status = "COMPLETED"
    run.evidence_status = response.evidence_status
    run.generation_mode = response.generation_mode
    run.model_id = response.model_id or ("oraclex-extractive-v1" if response.generation_mode == "EXTRACTIVE" else settings.OLLAMA_DEFAULT_MODEL)
    run.retrieval_mode = response.retrieval_mode
    run.requires_review = response.requires_review
    run.business_request_id = response.request_id
    run.source_version_ids = sorted({citation.version_id for citation in response.citations})
    run.completed_at = datetime.utcnow()
    max_clearance = conversation.classification_level
    if response.citations:
        clearances = db.query(Document.clearance_level).filter(
            Document.company_id == current_user.company_id,
            Document.id.in_({citation.document_id for citation in response.citations}),
        ).all()
        max_clearance = max([max_clearance, *[item[0] for item in clearances]])
    conversation.classification_level = max_clearance
    conversation.last_message_at = assistant_message.created_at
    conversation.updated_at = datetime.utcnow()
    for ordinal, citation in enumerate(response.citations, 1):
        db.add(AgentRunCitation(
            company_id=current_user.company_id,
            run_id=run.id,
            ordinal=ordinal,
            **citation.model_dump(),
        ))
    db.commit()
    response.conversation_id = conversation.id
    return response

@router.get("/health", response_model=AgentHealthResponse)
async def get_ai_health(_current_user: User = Depends(get_current_user)):
    """Returns the sovereign AI engine status, active model, and Ollama connection status."""
    return await llm_client.check_health()

@router.post("/feedback", response_model=FeedbackSubmitResponse)
def submit_agent_feedback(
    feedback: FeedbackSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Level 4: Governed institutional learning from accepted/rejected suggestions and human feedback."""
    record = FeedbackRecord(
        company_id=current_user.company_id,
        user_id=current_user.id,
        query_text=feedback.query_text,
        agent_response=feedback.agent_response,
        rating=feedback.rating,
        correction=feedback.correction,
        category=feedback.category
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"status": "recorded", "feedback_id": record.id}
