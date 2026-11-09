from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.permissions import user_can_access_document
from app.models.assistant import AgentRun, AgentRunCitation, Conversation, ConversationMessage
from app.models.company import User
from app.models.knowledge import Document
from app.schemas.agent import AgentCitation
from app.schemas.conversation import (
    ConversationDetailResponse,
    ConversationMessageResponse,
    ConversationSummaryResponse,
    PersistedAgentRunResponse,
)


REDACTED_ANSWER = "This saved answer is unavailable because your access to one or more cited sources has changed."


def _citation_schema(citation: AgentRunCitation) -> AgentCitation:
    return AgentCitation(
        document_id=citation.document_id,
        version_id=citation.version_id,
        chunk_id=citation.chunk_id,
        chunk_index=citation.chunk_index,
        title=citation.title,
        filename=citation.filename,
        page_number=citation.page_number,
        section_index=citation.section_index,
        sheet_name=citation.sheet_name,
        row_range=citation.row_range,
        source_type=citation.source_type,
        location_label=citation.location_label,
        excerpt=citation.excerpt,
        source_path=citation.source_path,
    )


def conversation_summary(conversation: Conversation) -> ConversationSummaryResponse:
    return ConversationSummaryResponse.model_validate(conversation)


def conversation_detail(db: Session, conversation: Conversation, user: User) -> ConversationDetailResponse:
    runs = db.query(AgentRun).filter(AgentRun.conversation_id == conversation.id).all()
    run_by_message = {run.response_message_id: run for run in runs if run.response_message_id}
    document_ids = {
        citation.document_id
        for run in runs
        for citation in run.citations
    }
    documents = (
        db.query(Document).filter(
            Document.company_id == user.company_id,
            Document.id.in_(document_ids),
        ).all()
        if document_ids
        else []
    )
    document_by_id = {document.id: document for document in documents}

    messages: list[ConversationMessageResponse] = []
    for message in conversation.messages:
        run = run_by_message.get(message.id)
        if not run:
            messages.append(ConversationMessageResponse.model_validate(message))
            continue
        allowed_citations = []
        for citation in run.citations:
            document = document_by_id.get(citation.document_id)
            if document and user_can_access_document(
                user,
                document.clearance_level,
                document.department_id,
                document.is_company_wide,
            ):
                allowed_citations.append(_citation_schema(citation))
        access_revoked = bool(run.citations) and len(allowed_citations) != len(run.citations)
        run_response = PersistedAgentRunResponse(
            id=run.id,
            status=run.status,
            evidence_status="ACCESS_REVOKED" if access_revoked else run.evidence_status,
            generation_mode=run.generation_mode,
            model_id=run.model_id,
            prompt_version=run.prompt_version,
            retrieval_mode=run.retrieval_mode,
            requires_review=bool(run.requires_review),
            business_request_id=run.business_request_id,
            safe_error_message=run.safe_error_message,
            citations=[] if access_revoked else allowed_citations,
        )
        messages.append(ConversationMessageResponse(
            id=message.id,
            role=message.role,
            content=REDACTED_ANSWER if access_revoked else message.content,
            sequence=message.sequence,
            created_at=message.created_at,
            run=run_response,
        ))

    return ConversationDetailResponse(
        **conversation_summary(conversation).model_dump(),
        messages=messages,
    )
