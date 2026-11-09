from __future__ import annotations

import uuid
import re
from typing import Optional

from sqlalchemy.orm import Session

from app.agents.context_injector import ContextInjector
from app.agents.data_agent import DataAgent
from app.agents.document_agent import DocumentAgent
from app.agents.verification import VerificationService
from app.models.company import User
from app.schemas.agent import AgentQueryResponse
from app.services.audit_service import record_audit_event
from app.services.request_service import create_request_draft


class AIOrchestrator:
    """Authorize, retrieve current evidence, answer, and record the outcome."""

    @classmethod
    async def process_query(
        cls,
        db: Session,
        user: User,
        query: str,
        conversation_id: Optional[str] = None,
        image_base64: Optional[str] = None,
        ip_address: str = "127.0.0.1",
        previous_questions: list[str] | None = None,
    ) -> AgentQueryResponse:
        conversation = conversation_id or str(uuid.uuid4())

        if image_base64:
            record_audit_event(
                db=db,
                company_id=user.company_id,
                action="ASSISTANT_UNSUPPORTED_INPUT",
                resource_type="ASSISTANT_QUERY",
                resource_id=conversation,
                user=user,
                details={"input_type": "image"},
                status="REJECTED",
                ip_address=ip_address,
            )
            return AgentQueryResponse(
                answer="Image analysis is not available in this release. Upload an approved text, PDF, CSV, or XLSX source to company documents instead.",
                conversation_id=conversation,
                evidence_status="UNSUPPORTED_INPUT",
                generation_mode="NONE",
                retrieval_mode="none",
                execution_status="UNSUPPORTED_INPUT",
            )

        verdict = VerificationService.verify_request(user, query)
        if not verdict.is_allowed:
            record_audit_event(
                db=db,
                company_id=user.company_id,
                action="ASSISTANT_ACCESS_BLOCKED",
                resource_type="ASSISTANT_QUERY",
                resource_id=conversation,
                user=user,
                details={"reason": verdict.violation_reason},
                status="BLOCKED",
                ip_address=ip_address,
            )
            return AgentQueryResponse(
                answer="I can't provide that information because you don't have access to it.",
                conversation_id=conversation,
                evidence_status="ACCESS_DENIED",
                generation_mode="NONE",
                retrieval_mode="none",
                execution_status="BLOCKED_CLEARANCE",
            )

        context = ContextInjector.build_context(db, user)
        query_lower = query.lower()
        previous_questions = (previous_questions or [])[-2:]
        follow_up_terms = {"that", "it", "again", "previous", "above", "same", "these", "those", "summarize", "explain", "more"}
        query_tokens = set(re.findall(r"[a-z0-9]+", query_lower))
        is_contextual_follow_up = bool(previous_questions) and (
            len(query_tokens) <= 10 or bool(query_tokens.intersection(follow_up_terms))
        )
        retrieval_query = " ".join([*previous_questions, query]) if is_contextual_follow_up else query
        numeric_intent = any(
            term in query_lower
            for term in ("data", "table", "metric", "yield", "count", "spreadsheet", "statistics", "budget", "percentage")
        )
        result = await (
            DataAgent.run(db, user, query, context["system_prompt"], retrieval_query, previous_questions if is_contextual_follow_up else None)
            if numeric_intent
            else DocumentAgent.run(
                db,
                user,
                query,
                context["system_prompt"],
                retrieval_query=retrieval_query,
                previous_questions=previous_questions if is_contextual_follow_up else None,
            )
        )

        request_id = None
        execution_status = "COMPLETED"
        final_answer = result.answer
        if verdict.requires_approval:
            request = create_request_draft(
                db,
                requester=user,
                request_type="CONTROLLED_CHANGE",
                title=verdict.approval_title or "Controlled operational change",
                description=verdict.approval_description or query,
                risk_level=verdict.risk_level,
                payload={
                    "affected_asset": None,
                    "proposed_change": query,
                    "business_reason": None,
                    "impact_assessment": None,
                    "rollback_plan": None,
                },
                source_context={
                    "conversation_id": conversation,
                    "evidence_version_ids": sorted({item.version_id for item in result.citations}),
                },
            )
            request_id = request.id
            execution_status = "DRAFT_CREATED"
            final_answer = (
                f"{result.answer}\n\n"
                "A typed request draft was created. Review and complete its required fields before submission. A later approval records only a decision; fulfillment is tracked separately."
            )

        final_answer = VerificationService.verify_output(final_answer, user)
        record_audit_event(
            db=db,
            company_id=user.company_id,
            action="ASSISTANT_QUERY",
            resource_type="ASSISTANT_QUERY",
            resource_id=request_id or conversation,
            user=user,
            details={
                "evidence_status": result.evidence_status,
                "generation_mode": result.generation_mode,
                "model_id": result.model_id,
                "version_ids": sorted({item.version_id for item in result.citations}),
                "citation_count": len(result.citations),
                "review_required": verdict.requires_approval,
                "request_id": request_id,
            },
            status="SUCCESS",
            ip_address=ip_address,
        )

        return AgentQueryResponse(
            answer=final_answer,
            conversation_id=conversation,
            evidence_status=result.evidence_status,
            generation_mode=result.generation_mode,
            model_id=result.model_id,
            retrieval_mode="hybrid" if result.citations else "none",
            citations=result.citations,
            requires_review=verdict.requires_approval,
            request_id=request_id,
            execution_status=execution_status,
        )
