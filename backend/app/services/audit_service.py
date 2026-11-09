from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.audit import AuditLog
from app.models.company import User

def record_audit_event(
    db: Session,
    company_id: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    user: Optional[User] = None,
    details: Optional[Dict[str, Any]] = None,
    status: str = "SUCCESS",
    ip_address: str = "127.0.0.1"
) -> AuditLog:
    """Creates a tamper-evident audit record."""
    details_dict = details or {}
    user_id = user.id if user else None
    user_email = user.email if user else "system"
    user_role = user.role.name if (user and user.role) else ("ADMIN" if (user and user.is_admin) else "ANONYMOUS")
    clearance_at_action = str(user.clearance_level) if user else "0"

    hash_payload = {
        "company_id": company_id,
        "user_id": user_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details_dict,
        "status": status
    }
    integrity_hash = AuditLog.calculate_hash(hash_payload)

    audit_entry = AuditLog(
        company_id=company_id,
        user_id=user_id,
        user_email=user_email,
        user_role=user_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details_dict,
        status=status,
        clearance_at_action=clearance_at_action,
        ip_address=ip_address,
        integrity_hash=integrity_hash
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    return audit_entry
