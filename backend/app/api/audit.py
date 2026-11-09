from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.company import User
from app.models.audit import AuditLog
from app.schemas.audit import AuditIntegrityResponse, AuditLogResponse
from app.api.deps import require_permission
from app.core.permissions import PermissionScope

router = APIRouter(prefix="/audit", tags=["Compliance & Audit Vault"])

@router.get("/logs", response_model=List[AuditLogResponse])
def get_audit_logs(
    action: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    before_timestamp: Optional[datetime] = None,
    before_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PermissionScope.AUDIT_VIEW))
):
    """Retrieves immutable audit trail entries."""
    query = db.query(AuditLog).filter(AuditLog.company_id == current_user.company_id)
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
    if status:
        query = query.filter(AuditLog.status == status)
    if (before_timestamp is None) != (before_id is None):
        raise HTTPException(status_code=422, detail="Both audit cursor fields are required.")
    if before_timestamp is not None and before_id is not None:
        query = query.filter(or_(
            AuditLog.timestamp < before_timestamp,
            and_(AuditLog.timestamp == before_timestamp, AuditLog.id < before_id),
        ))

    logs = query.order_by(AuditLog.timestamp.desc(), AuditLog.id.desc()).limit(limit).all()
    return [AuditLogResponse.model_validate(l) for l in logs]

@router.get("/verify-integrity", response_model=AuditIntegrityResponse)
def verify_audit_integrity(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PermissionScope.AUDIT_VIEW))
):
    """
    Verifies cryptographic SHA-256 integrity hash on all audit entries.
    Demonstrates tamper-evident sovereign compliance.
    """
    logs = db.query(AuditLog).filter(AuditLog.company_id == current_user.company_id).all()
    
    total = len(logs)
    valid_count = 0
    tampered_ids = []

    for log in logs:
        expected_hash = AuditLog.calculate_hash({
            "company_id": log.company_id,
            "user_id": log.user_id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details or {},
            "status": log.status
        })

        if log.integrity_hash == expected_hash:
            valid_count += 1
        else:
            tampered_ids.append(log.id)

    return {
        "status": "NO_RECORDS" if total == 0 else ("CHECKSUMS_VALID" if not tampered_ids else "TAMPER_DETECTED"),
        "total_records_checked": total,
        "valid_signatures": valid_count,
        "tampered_records": tampered_ids,
        "hash_algorithm": "SHA-256",
        "scope": "Individual record checksums only; deletion and reordering are not detected."
    }
