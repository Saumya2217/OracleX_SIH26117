from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime

class WorkflowResponse(BaseModel):
    id: str
    company_id: str
    department_id: Optional[str] = None
    title: str
    code: str
    description: Optional[str] = None
    category: str
    steps: List[Dict[str, Any]] = []
    requires_approval: bool
    approval_role_code: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class TaskResponse(BaseModel):
    id: str
    company_id: str
    department_id: Optional[str] = None
    assigned_to_id: Optional[str] = None
    created_by_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    project_name: str
    status: str
    priority: str
    due_date: Optional[datetime] = None
    assigned_to_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    project_name: str = "General Operations"
    assigned_to_id: Optional[str] = None
    department_id: Optional[str] = None
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    status: Literal["TODO", "IN_PROGRESS", "REVIEW", "COMPLETED"] = "TODO"

class TaskUpdate(BaseModel):
    status: Optional[Literal["TODO", "IN_PROGRESS", "REVIEW", "COMPLETED"]] = None
    priority: Optional[Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]] = None
    assigned_to_id: Optional[str] = None

class ApprovalRequestResponse(BaseModel):
    id: str
    company_id: str
    requester_id: str
    requester_name: Optional[str] = None
    approver_id: Optional[str] = None
    action_type: str
    title: str
    description: str
    risk_level: str
    payload: Dict[str, Any] = {}
    status: str
    rationale: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ApprovalResolveRequest(BaseModel):
    status: Literal["APPROVED", "REJECTED"]
    rationale: str = Field(min_length=3, max_length=2000)
