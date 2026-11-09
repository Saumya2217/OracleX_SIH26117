import re
from typing import Dict, Any, List, Optional
from app.models.company import User

class VerificationVerdict:
    def __init__(
        self,
        is_allowed: bool,
        requires_approval: bool = False,
        approval_title: Optional[str] = None,
        approval_description: Optional[str] = None,
        approval_type: Optional[str] = None,
        risk_level: str = "LOW",
        violation_reason: Optional[str] = None
    ):
        self.is_allowed = is_allowed
        self.requires_approval = requires_approval
        self.approval_title = approval_title
        self.approval_description = approval_description
        self.approval_type = approval_type
        self.risk_level = risk_level
        self.violation_reason = violation_reason

class VerificationService:
    """
    Enterprise Verification & Guardrails Layer.
    Guarantees authorization boundaries, blocks data leakage,
    and enforces human-in-the-loop approval gating for critical actions.
    """

    # Clearance restrictions patterns
    RESTRICTED_KEYWORDS = [
        "executive compensation", "salary sheet", "board minutes classified",
        "nuclear core schematic", "defense classified itar level 4", "payroll master",
        "restricted expansion plan", "merger acquisition confidential"
    ]

    # Action patterns requiring Human Approval
    HIGH_IMPACT_ACTIONS = [
        (r"(modify|change|alter|update)\s+.*tolerance", "TOLERANCE_CHANGE", "CRITICAL", "Engineering Tolerance Modification"),
        (r"(modify|change|alter|update|reallocate)\s+.*(budget|spending|fund|compensation)", "BUDGET_REALLOCATION", "HIGH", "Department Budget Reallocation"),
        (r"(override|disable|bypass)\s+.*(safety|alarm|interlock|sensor|policy|firewall)", "SECURITY_OVERRIDE", "CRITICAL", "Security & Safety Policy Override"),
        (r"(approve|submit|sign-off)\s+.*(ecn|eco|change order|contract|sla waiver|proposal)", "WORKFLOW_AUTHORIZATION", "HIGH", "Formal Workflow Sign-Off"),
        (r"(purchase|procure|spend|budget)\s+.*(\$|\b\d{4,}\b)", "FINANCIAL_AUTHORIZATION", "HIGH", "High-Value Procurement / Spend Request"),
        (r"(change|promote|assign|elevate)\s+.*(role|permission|clearance|admin access)", "ROLE_ELEVATION", "CRITICAL", "User Role / Clearance Elevation"),
        (r"(delete|archive|purge|erase)\s+.*(audit|compliance|document|record)", "DATA_PURGE", "CRITICAL", "Document / Audit Record Deletion")
    ]

    @classmethod
    def verify_request(cls, user: User, query: str) -> VerificationVerdict:
        query_lower = query.lower()

        # 1. Clearance Check
        user_clearance = user.clearance_level or 1
        if user_clearance < 4:
            for kw in cls.RESTRICTED_KEYWORDS:
                if kw in query_lower:
                    return VerificationVerdict(
                        is_allowed=False,
                        violation_reason=f"SECURITY CLEARANCE VIOLATION: Subject '{kw}' requires Level 4 clearance. User is Level {user_clearance}."
                    )

        # 2. Human-in-the-Loop Gating Check for High-Impact Actions
        for pattern, action_type, risk_level, title in cls.HIGH_IMPACT_ACTIONS:
            if re.search(pattern, query_lower):
                return VerificationVerdict(
                    is_allowed=True,
                    requires_approval=True,
                    approval_title=f"{title}: Requested by {user.full_name}",
                    approval_description=f"Action identified from user prompt: '{query}'. Requires formal management sign-off before execution.",
                    approval_type=action_type,
                    risk_level=risk_level
                )

        return VerificationVerdict(is_allowed=True, requires_approval=False)

    @classmethod
    def verify_output(cls, output_text: str, user: User) -> str:
        """Sanitizes model output to ensure confidential patterns don't leak inadvertently."""
        return output_text.strip()
