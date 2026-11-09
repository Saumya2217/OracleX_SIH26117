from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


RequestType = Literal["CONTROLLED_CHANGE", "ACCESS_REQUEST", "PURCHASE_REQUEST"]
RequestStatus = Literal["DRAFT", "SUBMITTED", "ASSIGNED", "APPROVED", "REJECTED", "CANCELLED", "COMPLETED"]
RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class ControlledChangePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    affected_asset: Optional[str] = Field(default=None, max_length=255)
    proposed_change: Optional[str] = Field(default=None, max_length=4000)
    business_reason: Optional[str] = Field(default=None, max_length=4000)
    impact_assessment: Optional[str] = Field(default=None, max_length=4000)
    rollback_plan: Optional[str] = Field(default=None, max_length=4000)


class AccessRequestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    resource: Optional[str] = Field(default=None, max_length=500)
    access_level: Optional[Literal["VIEW", "EDIT", "ADMIN"]] = None
    business_reason: Optional[str] = Field(default=None, max_length=4000)
    end_date: Optional[date] = None


class PurchaseRequestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    item: Optional[str] = Field(default=None, max_length=500)
    quantity: Optional[int] = Field(default=None, ge=1, le=1_000_000)
    estimated_cost: Optional[float] = Field(default=None, ge=0, le=1_000_000_000)
    currency: Optional[str] = Field(default=None, pattern=r"^[A-Z]{3}$")
    vendor: Optional[str] = Field(default=None, max_length=255)
    business_reason: Optional[str] = Field(default=None, max_length=4000)


class RequestInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class BusinessRequestCreate(RequestInput):
    request_type: RequestType
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=4000)
    risk_level: RiskLevel = "MEDIUM"
    assigned_reviewer_id: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)


class BusinessRequestUpdate(RequestInput):
    expected_lock_version: int = Field(ge=1)
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, min_length=1, max_length=4000)
    risk_level: Optional[RiskLevel] = None
    assigned_reviewer_id: Optional[str] = None
    payload: Optional[dict[str, Any]] = None


class RequestTransitionInput(RequestInput):
    expected_lock_version: int = Field(ge=1)


class RequestAssignInput(RequestTransitionInput):
    reviewer_id: str


class RequestReviewerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    full_name: str
    job_title: Optional[str] = None


class RequestDecisionInput(RequestTransitionInput):
    submitted_version_id: str
    decision: Literal["APPROVED", "REJECTED"]
    reason: str = Field(min_length=3, max_length=4000)


class RequestFulfillmentInput(RequestTransitionInput):
    notes: str = Field(min_length=3, max_length=4000)


class RequestCancelInput(RequestTransitionInput):
    reason: str = Field(min_length=3, max_length=2000)


class BusinessRequestVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    version_number: int
    payload: dict[str, Any]
    created_by_id: Optional[str] = None
    created_at: datetime


class BusinessRequestEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    event_type: str
    from_status: Optional[str] = None
    to_status: str
    reason: Optional[str] = None
    event_metadata: dict[str, Any]
    created_at: datetime


class BusinessRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    requester_id: str
    requester_name: Optional[str] = None
    assigned_reviewer_id: Optional[str] = None
    assigned_reviewer_name: Optional[str] = None
    request_type: RequestType
    title: str
    description: str
    risk_level: RiskLevel
    status: RequestStatus
    lock_version: int
    current_version_id: str
    submitted_version_id: Optional[str] = None
    source_context: dict[str, Any]
    submitted_at: Optional[datetime] = None
    decision: Optional[str] = None
    decision_reason: Optional[str] = None
    decided_by_id: Optional[str] = None
    decided_at: Optional[datetime] = None
    fulfilled_by_id: Optional[str] = None
    fulfillment_notes: Optional[str] = None
    fulfilled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    current_payload: dict[str, Any] = Field(default_factory=dict)


class BusinessRequestDetailResponse(BusinessRequestResponse):
    versions: list[BusinessRequestVersionResponse]
    timeline: list[BusinessRequestEventResponse]


class InternalNotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    notification_type: str
    title: str
    body: str
    deep_link: str
    request_id: Optional[str] = None
    read_at: Optional[datetime] = None
    created_at: datetime


PAYLOAD_MODELS = {
    "CONTROLLED_CHANGE": ControlledChangePayload,
    "ACCESS_REQUEST": AccessRequestPayload,
    "PURCHASE_REQUEST": PurchaseRequestPayload,
}

REQUIRED_PAYLOAD_FIELDS = {
    "CONTROLLED_CHANGE": ("affected_asset", "proposed_change", "business_reason", "impact_assessment", "rollback_plan"),
    "ACCESS_REQUEST": ("resource", "access_level", "business_reason"),
    "PURCHASE_REQUEST": ("item", "quantity", "estimated_cost", "currency", "business_reason"),
}


def normalize_request_payload(request_type: str, payload: dict[str, Any], *, require_complete: bool) -> dict[str, Any]:
    model = PAYLOAD_MODELS[request_type]
    normalized = model.model_validate(payload).model_dump(mode="json", exclude_none=True)
    if require_complete:
        missing = [field for field in REQUIRED_PAYLOAD_FIELDS[request_type] if normalized.get(field) in (None, "")]
        if missing:
            raise ValueError(f"Complete these required fields before submission: {', '.join(missing)}.")
    return normalized
