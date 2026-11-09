from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel
from datetime import datetime

class AuditIntegrityResponse(BaseModel):
    status: Literal["NO_RECORDS", "CHECKSUMS_VALID", "TAMPER_DETECTED"]
    total_records_checked: int
    valid_signatures: int
    tampered_records: list[str]
    hash_algorithm: str
    scope: str

class AuditLogResponse(BaseModel):
    id: str
    company_id: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    user_role: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Dict[str, Any] = {}
    status: str
    clearance_at_action: Optional[str] = None
    ip_address: str
    integrity_hash: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True
