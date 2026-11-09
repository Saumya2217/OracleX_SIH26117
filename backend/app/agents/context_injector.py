from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.company import Company, User, Department, Role

class ContextInjector:
    """
    Builds structured organizational context around user queries.
    Never passes raw unconstrained prompts to the LLM.
    """
    @staticmethod
    def build_context(db: Session, user: User) -> Dict[str, Any]:
        company = db.query(Company).filter(Company.id == user.company_id).first()
        dept = db.query(Department).filter(Department.id == user.department_id).first() if user.department_id else None
        role = db.query(Role).filter(Role.id == user.role_id).first() if user.role_id else None
        supervisor = db.query(User).filter(User.id == user.reports_to_id).first() if user.reports_to_id else None

        company_info = {
            "name": company.name if company else "OracleX Sovereign Enterprise",
            "industry": company.industry if company else "Confidential Industry",
            "compliance_standards": company.compliance_standards if company else [],
            "description": company.description if company else ""
        }

        user_info = {
            "user_id": user.id,
            "name": user.full_name,
            "email": user.email,
            "job_title": user.job_title or "Staff Member",
            "department": dept.name if dept else "General",
            "department_code": dept.code if dept else "GEN",
            "role": role.name if role else ("Administrator" if user.is_admin else "Employee"),
            "clearance_level": user.clearance_level or 1,
            "supervisor": supervisor.full_name if supervisor else "Executive Board",
            "is_admin": user.is_admin,
            "permissions": role.permissions if role else []
        }

        system_prompt = (
            f"You are ORACLEX, the sovereign on-premise AI assistant for {company_info['name']} "
            f"({company_info['industry']}).\n\n"
            f"CURRENT USER CONTEXT:\n"
            f"- Name: {user_info['name']} ({user_info['job_title']})\n"
            f"- Department: {user_info['department']}\n"
            f"- Role: {user_info['role']}\n\n"
            f"OPERATIONAL DIRECTIVES:\n"
            f"1. You answer questions accurately, directly, and concisely using the provided company documents.\n"
            f"2. Keep responses short, factual, and relevant (1-3 sentences or bullets). No unnecessary filler.\n"
            f"3. For general conceptual questions, explain clearly and concisely.\n"
            f"4. If citing company documents, cite simply: 'Source: filename.txt'."
        )

        return {
            "company": company_info,
            "user": user_info,
            "system_prompt": system_prompt
        }
