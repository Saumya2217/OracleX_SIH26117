from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.permissions import PermissionScope, user_has_permission
from app.models.company import User
from app.models.request import (
    BusinessRequest,
    BusinessRequestEvent,
    BusinessRequestVersion,
    InternalNotification,
    generate_uuid,
)
from app.schemas.request import normalize_request_payload


def eligible_reviewer(db: Session, company_id: str, reviewer_id: str, requester_id: str) -> User:
    reviewer = db.query(User).filter(
        User.id == reviewer_id,
        User.company_id == company_id,
        User.is_active == True,
    ).first()
    if not reviewer or not user_has_permission(reviewer, PermissionScope.WORKFLOW_APPROVE):
        raise HTTPException(status_code=422, detail="The assigned reviewer is not an active authorized reviewer in this company.")
    if reviewer.id == requester_id:
        raise HTTPException(status_code=422, detail="A requester cannot be assigned to review their own request.")
    return reviewer


def request_snapshot(
    *,
    request_type: str,
    title: str,
    description: str,
    risk_level: str,
    assigned_reviewer_id: str | None,
    fields: dict[str, Any],
) -> dict[str, Any]:
    return {
        "request_type": request_type,
        "title": title,
        "description": description,
        "risk_level": risk_level,
        "assigned_reviewer_id": assigned_reviewer_id,
        "fields": fields,
    }


def add_event(
    db: Session,
    request: BusinessRequest,
    *,
    actor_id: str | None,
    event_type: str,
    from_status: str | None,
    to_status: str,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> BusinessRequestEvent:
    event = BusinessRequestEvent(
        company_id=request.company_id,
        request_id=request.id,
        actor_id=actor_id,
        event_type=event_type,
        from_status=from_status,
        to_status=to_status,
        reason=reason,
        event_metadata=metadata or {},
    )
    db.add(event)
    return event


def notify(
    db: Session,
    request: BusinessRequest,
    *,
    recipient_id: str,
    notification_type: str,
    title: str,
    body: str,
) -> None:
    db.add(InternalNotification(
        company_id=request.company_id,
        recipient_id=recipient_id,
        request_id=request.id,
        notification_type=notification_type,
        title=title,
        body=body,
        deep_link=f"/requests/{request.id}",
    ))


def create_request_draft(
    db: Session,
    *,
    requester: User,
    request_type: str,
    title: str,
    description: str,
    risk_level: str,
    payload: dict[str, Any],
    assigned_reviewer_id: str | None = None,
    source_context: dict[str, Any] | None = None,
    commit: bool = True,
) -> BusinessRequest:
    normalized = normalize_request_payload(request_type, payload, require_complete=False)
    if assigned_reviewer_id:
        eligible_reviewer(db, requester.company_id, assigned_reviewer_id, requester.id)

    request_id = generate_uuid()
    version_id = generate_uuid()
    request = BusinessRequest(
        id=request_id,
        company_id=requester.company_id,
        requester_id=requester.id,
        assigned_reviewer_id=assigned_reviewer_id,
        request_type=request_type,
        title=title.strip(),
        description=description.strip(),
        risk_level=risk_level,
        status="DRAFT",
        lock_version=1,
        current_version_id=version_id,
        source_context=source_context or {},
    )
    version = BusinessRequestVersion(
        id=version_id,
        company_id=requester.company_id,
        request_id=request_id,
        version_number=1,
        payload=request_snapshot(
            request_type=request_type,
            title=request.title,
            description=request.description,
            risk_level=risk_level,
            assigned_reviewer_id=assigned_reviewer_id,
            fields=normalized,
        ),
        created_by_id=requester.id,
    )
    db.add_all([request, version])
    add_event(
        db,
        request,
        actor_id=requester.id,
        event_type="DRAFT_CREATED",
        from_status=None,
        to_status="DRAFT",
        metadata={"version_id": version_id, "version_number": 1},
    )
    if commit:
        db.commit()
        db.refresh(request)
    return request
