from enum import Enum
from typing import Optional
from app.models.company import User, Role

class ClearanceLevel(int, Enum):
    PUBLIC = 1
    INTERNAL = 2
    CONFIDENTIAL = 3
    RESTRICTED = 4

class PermissionScope:
    # Documents
    DOC_READ = "doc:read"
    DOC_UPLOAD = "doc:upload"
    DOC_DELETE = "doc:delete"
    DOC_RESTRICTED = "doc:restricted"
    
    # AI & Agents
    AGENT_RUN = "agent:run"
    AGENT_DIRECT_TOOL = "agent:direct_tool"
    
    # Workflows & Approvals
    WORKFLOW_TRIGGER = "workflow:trigger"
    WORKFLOW_APPROVE = "workflow:approve"
    WORKFLOW_MANAGE = "workflow:manage"
    
    # Tasks
    TASK_CREATE = "task:create"
    TASK_ASSIGN = "task:assign"
    TASK_MANAGE = "task:manage"
    
    # Organization
    ORG_MANAGE = "org:manage"
    ROLE_ASSIGN = "role:assign"
    
    # Adaptation (Levels 3 & 4)
    ADAPTATION_PROPOSE = "adaptation:propose"
    ADAPTATION_REVIEW = "adaptation:review"
    
    # Audit & Security
    AUDIT_VIEW = "audit:view"
    AUDIT_EXPORT = "audit:export"

# Default permission sets for role templates
DEFAULT_ROLE_PERMISSIONS = {
    "ADMIN": [
        PermissionScope.DOC_READ, PermissionScope.DOC_UPLOAD, PermissionScope.DOC_DELETE, PermissionScope.DOC_RESTRICTED,
        PermissionScope.AGENT_RUN, PermissionScope.AGENT_DIRECT_TOOL,
        PermissionScope.WORKFLOW_TRIGGER, PermissionScope.WORKFLOW_APPROVE, PermissionScope.WORKFLOW_MANAGE,
        PermissionScope.TASK_CREATE, PermissionScope.TASK_ASSIGN, PermissionScope.TASK_MANAGE,
        PermissionScope.ORG_MANAGE, PermissionScope.ROLE_ASSIGN,
        PermissionScope.ADAPTATION_PROPOSE, PermissionScope.ADAPTATION_REVIEW,
        PermissionScope.AUDIT_VIEW, PermissionScope.AUDIT_EXPORT
    ],
    "MANAGER": [
        PermissionScope.DOC_READ, PermissionScope.DOC_UPLOAD,
        PermissionScope.AGENT_RUN,
        PermissionScope.WORKFLOW_TRIGGER, PermissionScope.WORKFLOW_APPROVE,
        PermissionScope.TASK_CREATE, PermissionScope.TASK_ASSIGN,
        PermissionScope.ADAPTATION_PROPOSE, PermissionScope.ADAPTATION_REVIEW,
        PermissionScope.AUDIT_VIEW
    ],
    "EMPLOYEE": [
        PermissionScope.DOC_READ,
        PermissionScope.AGENT_RUN,
        PermissionScope.WORKFLOW_TRIGGER,
        PermissionScope.TASK_CREATE
    ],
    "TECHNICIAN": [
        PermissionScope.DOC_READ,
        PermissionScope.AGENT_RUN,
        PermissionScope.WORKFLOW_TRIGGER,
        PermissionScope.TASK_CREATE
    ],
    "ANALYST": [
        PermissionScope.DOC_READ, PermissionScope.DOC_UPLOAD,
        PermissionScope.AGENT_RUN,
        PermissionScope.TASK_CREATE,
        PermissionScope.ADAPTATION_PROPOSE
    ]
}

def user_has_permission(user: User, required_scope: str) -> bool:
    """Checks whether the user possesses the required permission scope."""
    if not user or not user.is_active:
        return False
    if user.is_admin:
        return True
    
    user_perms = []
    if user.role and user.role.permissions:
        user_perms = user.role.permissions
    
    return required_scope in user_perms

def user_can_access_clearance(user: User, target_clearance: int) -> bool:
    """Checks if user clearance level meets or exceeds target document clearance level."""
    if not user or not user.is_active:
        return False
    if user.is_admin:
        return True
    
    return (user.clearance_level or 1) >= target_clearance

def user_can_access_document(user: User, doc_clearance: int, doc_department_id: Optional[str], is_company_wide: bool) -> bool:
    """Verifies dual conditions: clearance level + departmental boundaries."""
    if not user or not user.is_active:
        return False
    if user.is_admin:
        return True
    
    # 1. Clearance check
    if not user_can_access_clearance(user, doc_clearance):
        return False
    
    # 2. Scope / Department check
    if is_company_wide:
        return True
    
    if doc_department_id and user.department_id == doc_department_id:
        return True
        
    return False
