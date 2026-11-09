from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.api.deps import get_current_user
from app.core.permissions import PermissionScope, user_has_permission
from app.database import get_db
from app.models.company import User
from app.models.request import BusinessRequest, BusinessRequestVersion, InternalNotification, generate_uuid
from app.schemas.request import (
    BusinessRequestCreate,
    BusinessRequestDetailResponse,
    BusinessRequestEventResponse,
    BusinessRequestResponse,
    BusinessRequestUpdate,
    BusinessRequestVersionResponse,
    InternalNotificationResponse,
    RequestAssignInput,
    RequestCancelInput,
    RequestDecisionInput,
    RequestFulfillmentInput,
    RequestTransitionInput,
    RequestReviewerResponse,
    normalize_request_payload,
)
from app.services.audit_service import record_audit_event
from app.services.request_service import (
    add_event,
    create_request_draft,
    eligible_reviewer,
    notify,
    request_snapshot,
)


router = APIRouter(prefix="/requests", tags=["Accountable requests"])


def _current_version(db: Session, request: BusinessRequest) -> BusinessRequestVersion:
    version = db.query(BusinessRequestVersion).filter(
        BusinessRequestVersion.id == request.current_version_id,
        BusinessRequestVersion.request_id == request.id,
    ).first()
    if not version:
        raise HTTPException(status_code=500, detail="The request version record is unavailable.")
    return version


def _can_view(user: User, request: BusinessRequest) -> bool:
    if request.requester_id == user.id or request.assigned_reviewer_id == user.id:
        return True
    return request.status != "DRAFT" and user_has_permission(user, PermissionScope.WORKFLOW_APPROVE)


def _get_request(db: Session, user: User, request_id: str, *, require_view: bool = True) -> BusinessRequest:
    request = db.query(BusinessRequest).filter(
        BusinessRequest.id == request_id,
        BusinessRequest.company_id == user.company_id,
    ).first()
    if not request or (require_view and not _can_view(user, request)):
        raise HTTPException(status_code=404, detail="Request not found.")
    return request


def _serialize(db: Session, request: BusinessRequest) -> BusinessRequestResponse:
    current = _current_version(db, request)
    response = BusinessRequestResponse.model_validate(request)
    response.requester_name = request.requester.full_name if request.requester else None
    response.assigned_reviewer_name = request.assigned_reviewer.full_name if request.assigned_reviewer else None
    response.current_payload = dict(current.payload or {}).get("fields", {})
    return response


def _detail(db: Session, request: BusinessRequest) -> BusinessRequestDetailResponse:
    base = _serialize(db, request).model_dump()
    timeline = []
    for event in request.events:
        item = BusinessRequestEventResponse.model_validate(event)
        item.actor_name = event.actor.full_name if event.actor else "System"
        timeline.append(item)
    return BusinessRequestDetailResponse(
        **base,
        versions=[BusinessRequestVersionResponse.model_validate(item) for item in request.versions],
        timeline=timeline,
    )


def _stale() -> HTTPException:
    return HTTPException(status_code=409, detail="This request changed after you opened it. Reload and review the latest version.")


def _validated_fields(request_type: str, fields: dict, *, require_complete: bool = False) -> dict:
    try:
        return normalize_request_payload(request_type, fields, require_complete=require_complete)
    except ValidationError as exc:
        errors = [
            {"loc": ["body", "payload", *item["loc"]],
             "msg": "Use a three-letter currency code, such as USD." if item["loc"] == ("currency",) and item["type"] == "string_pattern_mismatch" else item["msg"],
             "type": item["type"]}
            for item in exc.errors(include_input=False, include_context=False, include_url=False)
        ]
        raise HTTPException(status_code=422, detail=errors) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("", response_model=list[BusinessRequestResponse])
def list_requests(
    view: Literal["mine", "review"] = Query("mine"),
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(BusinessRequest).filter(BusinessRequest.company_id == current_user.company_id)
    if view == "mine":
        query = query.filter(BusinessRequest.requester_id == current_user.id)
    else:
        if not user_has_permission(current_user, PermissionScope.WORKFLOW_APPROVE):
            raise HTTPException(status_code=403, detail="Request review permission required.")
        query = query.filter(
            BusinessRequest.status != "DRAFT",
            or_(BusinessRequest.assigned_reviewer_id == current_user.id, BusinessRequest.assigned_reviewer_id.is_(None)),
        )
    if status_filter:
        query = query.filter(BusinessRequest.status == status_filter)
    return [_serialize(db, item) for item in query.order_by(BusinessRequest.updated_at.desc()).all()]


@router.post("", response_model=BusinessRequestDetailResponse, status_code=201)
def create_request(
    payload: BusinessRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not user_has_permission(current_user, PermissionScope.WORKFLOW_TRIGGER):
        raise HTTPException(status_code=403, detail="Request creation permission required.")
    request = create_request_draft(
        db,
        requester=current_user,
        request_type=payload.request_type,
        title=payload.title,
        description=payload.description,
        risk_level=payload.risk_level,
        payload=_validated_fields(payload.request_type, payload.payload),
        assigned_reviewer_id=payload.assigned_reviewer_id,
    )
    record_audit_event(
        db=db,
        company_id=current_user.company_id,
        action="REQUEST_DRAFT_CREATE",
        resource_type="BUSINESS_REQUEST",
        resource_id=request.id,
        user=current_user,
        details={"request_type": request.request_type, "version_id": request.current_version_id},
    )
    return _detail(db, request)


@router.get("/reviewers/eligible", response_model=list[RequestReviewerResponse])
def list_eligible_reviewers(
    request_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (user_has_permission(current_user, PermissionScope.WORKFLOW_TRIGGER)
            or user_has_permission(current_user, PermissionScope.WORKFLOW_APPROVE)):
        raise HTTPException(status_code=403, detail="Request creation or review permission required.")
    requester_id = _get_request(db, current_user, request_id).requester_id if request_id else current_user.id
    candidates = db.query(User).filter(
        User.company_id == current_user.company_id, User.is_active == True, User.id != requester_id,
    ).order_by(User.full_name, User.id).all()
    return [user for user in candidates if user_has_permission(user, PermissionScope.WORKFLOW_APPROVE)]


@router.get("/{request_id}", response_model=BusinessRequestDetailResponse)
def get_request(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _detail(db, _get_request(db, current_user, request_id))


@router.patch("/{request_id}", response_model=BusinessRequestDetailResponse)
def update_request_draft(
    request_id: str,
    payload: BusinessRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    request = _get_request(db, current_user, request_id)
    if request.requester_id != current_user.id or request.status != "DRAFT":
        raise HTTPException(status_code=409, detail="Only the requester can edit a draft request.")
    if request.lock_version != payload.expected_lock_version:
        raise _stale()
    reviewer_id = payload.assigned_reviewer_id if "assigned_reviewer_id" in payload.model_fields_set else request.assigned_reviewer_id
    if reviewer_id:
        eligible_reviewer(db, request.company_id, reviewer_id, request.requester_id)
    current_fields = dict(_current_version(db, request).payload or {}).get("fields", {})
    fields = _validated_fields(
        request.request_type,
        payload.payload if payload.payload is not None else current_fields,
        require_complete=False,
    )
    title = payload.title or request.title
    description = payload.description or request.description
    risk_level = payload.risk_level or request.risk_level
    version_id = generate_uuid()
    next_number = len(request.versions) + 1
    updated = db.query(BusinessRequest).filter(
        BusinessRequest.id == request.id,
        BusinessRequest.lock_version == payload.expected_lock_version,
        BusinessRequest.status == "DRAFT",
    ).update({
        BusinessRequest.title: title,
        BusinessRequest.description: description,
        BusinessRequest.risk_level: risk_level,
        BusinessRequest.assigned_reviewer_id: reviewer_id,
        BusinessRequest.current_version_id: version_id,
        BusinessRequest.lock_version: payload.expected_lock_version + 1,
        BusinessRequest.updated_at: datetime.utcnow(),
    }, synchronize_session=False)
    if updated != 1:
        db.rollback()
        raise _stale()
    db.add(BusinessRequestVersion(
        id=version_id,
        company_id=request.company_id,
        request_id=request.id,
        version_number=next_number,
        payload=request_snapshot(
            request_type=request.request_type,
            title=title,
            description=description,
            risk_level=risk_level,
            assigned_reviewer_id=reviewer_id,
            fields=fields,
        ),
        created_by_id=current_user.id,
    ))
    add_event(
        db,
        request,
        actor_id=current_user.id,
        event_type="DRAFT_UPDATED",
        from_status="DRAFT",
        to_status="DRAFT",
        metadata={"version_id": version_id, "version_number": next_number},
    )
    db.commit()
    db.expire_all()
    request = _get_request(db, current_user, request_id)
    return _detail(db, request)


@router.post("/{request_id}/submit", response_model=BusinessRequestDetailResponse)
def submit_request(
    request_id: str,
    payload: RequestTransitionInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    request = _get_request(db, current_user, request_id)
    if request.requester_id != current_user.id or request.status != "DRAFT":
        raise HTTPException(status_code=409, detail="Only the requester can submit a draft request.")
    current = _current_version(db, request)
    fields = dict(current.payload or {}).get("fields", {})
    _validated_fields(request.request_type, fields, require_complete=True)
    if request.assigned_reviewer_id:
        eligible_reviewer(db, request.company_id, request.assigned_reviewer_id, request.requester_id)
    target_status = "ASSIGNED" if request.assigned_reviewer_id else "SUBMITTED"
    now = datetime.utcnow()
    updated = db.query(BusinessRequest).filter(
        BusinessRequest.id == request.id,
        BusinessRequest.lock_version == payload.expected_lock_version,
        BusinessRequest.status == "DRAFT",
    ).update({
        BusinessRequest.status: target_status,
        BusinessRequest.submitted_version_id: current.id,
        BusinessRequest.submitted_at: now,
        BusinessRequest.lock_version: payload.expected_lock_version + 1,
        BusinessRequest.updated_at: now,
    }, synchronize_session=False)
    if updated != 1:
        db.rollback()
        raise _stale()
    add_event(
        db,
        request,
        actor_id=current_user.id,
        event_type="SUBMITTED",
        from_status="DRAFT",
        to_status=target_status,
        metadata={"submitted_version_id": current.id},
    )
    if request.assigned_reviewer_id:
        notify(
            db,
            request,
            recipient_id=request.assigned_reviewer_id,
            notification_type="REQUEST_ASSIGNED",
            title=f"Review assigned: {request.title}",
            body=f"{current_user.full_name} submitted a {request.request_type.lower().replace('_', ' ')} request for your review.",
        )
    else:
        reviewers = db.query(User).filter(User.company_id == request.company_id, User.is_active == True).all()
        for reviewer in reviewers:
            if reviewer.id != request.requester_id and user_has_permission(reviewer, PermissionScope.WORKFLOW_APPROVE):
                notify(
                    db,
                    request,
                    recipient_id=reviewer.id,
                    notification_type="REQUEST_SUBMITTED",
                    title=f"Request ready for assignment: {request.title}",
                    body=f"{current_user.full_name} submitted a request for review.",
                )
    db.commit()
    db.expire_all()
    request = _get_request(db, current_user, request_id)
    record_audit_event(
        db=db,
        company_id=current_user.company_id,
        action="REQUEST_SUBMIT",
        resource_type="BUSINESS_REQUEST",
        resource_id=request.id,
        user=current_user,
        details={"submitted_version_id": request.submitted_version_id, "status": request.status},
    )
    return _detail(db, request)


@router.post("/{request_id}/assign", response_model=BusinessRequestDetailResponse)
def assign_request(
    request_id: str,
    payload: RequestAssignInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not user_has_permission(current_user, PermissionScope.WORKFLOW_APPROVE):
        raise HTTPException(status_code=403, detail="Request review permission required.")
    request = _get_request(db, current_user, request_id)
    if request.status not in {"SUBMITTED", "ASSIGNED"}:
        raise HTTPException(status_code=409, detail="Only submitted requests can be assigned.")
    if request.assigned_reviewer_id and request.assigned_reviewer_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only the assigned reviewer or an administrator can reassign this request.")
    reviewer = eligible_reviewer(db, request.company_id, payload.reviewer_id, request.requester_id)
    if request.lock_version != payload.expected_lock_version:
        raise _stale()
    if request.assigned_reviewer_id == reviewer.id:
        raise HTTPException(status_code=409, detail="This reviewer is already assigned.")
    previous_reviewer_id = request.assigned_reviewer_id
    prior = request.status
    updated = db.query(BusinessRequest).filter(
        BusinessRequest.id == request.id,
        BusinessRequest.lock_version == payload.expected_lock_version,
        BusinessRequest.status.in_(["SUBMITTED", "ASSIGNED"]),
    ).update({
        BusinessRequest.assigned_reviewer_id: reviewer.id,
        BusinessRequest.status: "ASSIGNED",
        BusinessRequest.lock_version: payload.expected_lock_version + 1,
        BusinessRequest.updated_at: datetime.utcnow(),
    }, synchronize_session=False)
    if updated != 1:
        db.rollback()
        raise _stale()
    add_event(db, request, actor_id=current_user.id, event_type="ASSIGNED", from_status=prior, to_status="ASSIGNED", reason=f"Review assigned to {reviewer.full_name}.", metadata={"reviewer_id": reviewer.id, "previous_reviewer_id": previous_reviewer_id})
    notify(db, request, recipient_id=reviewer.id, notification_type="REQUEST_ASSIGNED", title=f"Review assigned: {request.title}", body=f"{current_user.full_name} assigned this request to you.")
    if previous_reviewer_id:
        notify(db, request, recipient_id=previous_reviewer_id, notification_type="REQUEST_REASSIGNED", title=f"Review reassigned: {request.title}", body=f"{reviewer.full_name} is now the assigned reviewer.")
    notify(db, request, recipient_id=request.requester_id, notification_type="REQUEST_REVIEWER_CHANGED", title=f"Reviewer updated: {request.title}", body=f"{reviewer.full_name} is now reviewing your request.")
    db.commit()
    db.expire_all()
    return _detail(db, _get_request(db, current_user, request_id))


@router.post("/{request_id}/decision", response_model=BusinessRequestDetailResponse)
def decide_request(
    request_id: str,
    payload: RequestDecisionInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not user_has_permission(current_user, PermissionScope.WORKFLOW_APPROVE):
        raise HTTPException(status_code=403, detail="Request review permission required.")
    request = _get_request(db, current_user, request_id)
    if request.requester_id == current_user.id:
        raise HTTPException(status_code=403, detail="Requesters cannot decide their own requests.")
    if request.status not in {"SUBMITTED", "ASSIGNED"}:
        raise HTTPException(status_code=409, detail="This request is not awaiting a decision.")
    if request.assigned_reviewer_id and request.assigned_reviewer_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="This request is assigned to another reviewer.")
    if payload.submitted_version_id != request.submitted_version_id:
        raise HTTPException(status_code=409, detail="The decision does not reference the submitted request version.")
    prior = request.status
    now = datetime.utcnow()
    updated = db.query(BusinessRequest).filter(
        BusinessRequest.id == request.id,
        BusinessRequest.lock_version == payload.expected_lock_version,
        BusinessRequest.status.in_(["SUBMITTED", "ASSIGNED"]),
        BusinessRequest.submitted_version_id == payload.submitted_version_id,
    ).update({
        BusinessRequest.status: payload.decision,
        BusinessRequest.decision: payload.decision,
        BusinessRequest.decision_reason: payload.reason,
        BusinessRequest.decided_by_id: current_user.id,
        BusinessRequest.decided_at: now,
        BusinessRequest.lock_version: payload.expected_lock_version + 1,
        BusinessRequest.updated_at: now,
    }, synchronize_session=False)
    if updated != 1:
        db.rollback()
        raise _stale()
    add_event(
        db,
        request,
        actor_id=current_user.id,
        event_type="DECIDED",
        from_status=prior,
        to_status=payload.decision,
        reason=payload.reason,
        metadata={"submitted_version_id": payload.submitted_version_id, "decision": payload.decision},
    )
    notify(
        db,
        request,
        recipient_id=request.requester_id,
        notification_type="REQUEST_DECIDED",
        title=f"Request {payload.decision.lower()}: {request.title}",
        body=payload.reason,
    )
    db.commit()
    db.expire_all()
    request = _get_request(db, current_user, request_id)
    record_audit_event(
        db=db,
        company_id=current_user.company_id,
        action=f"REQUEST_{payload.decision}",
        resource_type="BUSINESS_REQUEST",
        resource_id=request.id,
        user=current_user,
        details={"submitted_version_id": payload.submitted_version_id, "reason": payload.reason},
    )
    return _detail(db, request)


@router.post("/{request_id}/fulfill", response_model=BusinessRequestDetailResponse)
def fulfill_request(
    request_id: str,
    payload: RequestFulfillmentInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not user_has_permission(current_user, PermissionScope.WORKFLOW_APPROVE):
        raise HTTPException(status_code=403, detail="Request fulfillment permission required.")
    request = _get_request(db, current_user, request_id)
    if request.status != "APPROVED":
        raise HTTPException(status_code=409, detail="Only an approved request can be marked completed.")
    now = datetime.utcnow()
    updated = db.query(BusinessRequest).filter(
        BusinessRequest.id == request.id,
        BusinessRequest.lock_version == payload.expected_lock_version,
        BusinessRequest.status == "APPROVED",
        BusinessRequest.fulfilled_at.is_(None),
    ).update({
        BusinessRequest.status: "COMPLETED",
        BusinessRequest.fulfilled_by_id: current_user.id,
        BusinessRequest.fulfillment_notes: payload.notes,
        BusinessRequest.fulfilled_at: now,
        BusinessRequest.lock_version: payload.expected_lock_version + 1,
        BusinessRequest.updated_at: now,
    }, synchronize_session=False)
    if updated != 1:
        db.rollback()
        raise _stale()
    add_event(db, request, actor_id=current_user.id, event_type="FULFILLED", from_status="APPROVED", to_status="COMPLETED", reason=payload.notes)
    notify(db, request, recipient_id=request.requester_id, notification_type="REQUEST_COMPLETED", title=f"Request completed: {request.title}", body=payload.notes)
    db.commit()
    db.expire_all()
    request = _get_request(db, current_user, request_id)
    record_audit_event(
        db=db,
        company_id=current_user.company_id,
        action="REQUEST_FULFILLED",
        resource_type="BUSINESS_REQUEST",
        resource_id=request.id,
        user=current_user,
        details={"notes": payload.notes},
    )
    return _detail(db, request)


@router.post("/{request_id}/cancel", response_model=BusinessRequestDetailResponse)
def cancel_request(
    request_id: str,
    payload: RequestCancelInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    request = _get_request(db, current_user, request_id)
    if request.requester_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the requester can cancel this request.")
    if request.status not in {"DRAFT", "SUBMITTED", "ASSIGNED"}:
        raise HTTPException(status_code=409, detail="This request can no longer be cancelled.")
    prior = request.status
    now = datetime.utcnow()
    updated = db.query(BusinessRequest).filter(
        BusinessRequest.id == request.id,
        BusinessRequest.lock_version == payload.expected_lock_version,
        BusinessRequest.status.in_(["DRAFT", "SUBMITTED", "ASSIGNED"]),
    ).update({
        BusinessRequest.status: "CANCELLED",
        BusinessRequest.cancelled_at: now,
        BusinessRequest.lock_version: payload.expected_lock_version + 1,
        BusinessRequest.updated_at: now,
    }, synchronize_session=False)
    if updated != 1:
        db.rollback()
        raise _stale()
    add_event(db, request, actor_id=current_user.id, event_type="CANCELLED", from_status=prior, to_status="CANCELLED", reason=payload.reason)
    if request.assigned_reviewer_id:
        notify(db, request, recipient_id=request.assigned_reviewer_id, notification_type="REQUEST_CANCELLED", title=f"Request cancelled: {request.title}", body=payload.reason)
    db.commit()
    db.expire_all()
    return _detail(db, _get_request(db, current_user, request_id))


@router.get("/notifications/inbox", response_model=list[InternalNotificationResponse])
def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=100),
    before_created_at: datetime | None = None,
    before_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(InternalNotification).filter(
        InternalNotification.company_id == current_user.company_id,
        InternalNotification.recipient_id == current_user.id,
    )
    if unread_only:
        query = query.filter(InternalNotification.read_at.is_(None))
    if (before_created_at is None) != (before_id is None):
        raise HTTPException(status_code=422, detail="Both notification cursor fields are required.")
    if before_created_at is not None:
        query = query.filter(or_(
            InternalNotification.created_at < before_created_at,
            and_(InternalNotification.created_at == before_created_at, InternalNotification.id < before_id),
        ))
    return query.order_by(InternalNotification.created_at.desc(), InternalNotification.id.desc()).limit(limit).all()


@router.post("/notifications/{notification_id}/read", response_model=InternalNotificationResponse)
def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = db.query(InternalNotification).filter(
        InternalNotification.id == notification_id,
        InternalNotification.company_id == current_user.company_id,
        InternalNotification.recipient_id == current_user.id,
    ).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found.")
    if not notification.read_at:
        notification.read_at = datetime.utcnow()
        db.commit()
        db.refresh(notification)
    return notification
