import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.company import User, Role, Company, Department
from app.core.security import verify_password, create_access_token, hash_password
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse, CompanyRegisterRequest, BootstrapStatusResponse
from app.api.deps import get_current_user
from app.services.audit_service import record_audit_event
from app.config import settings
from app.core.permissions import DEFAULT_ROLE_PERMISSIONS

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/bootstrap-status", response_model=BootstrapStatusResponse)
def bootstrap_status(db: Session = Depends(get_db)):
    company_exists = db.query(Company.id).first() is not None
    return {"enabled": bool(settings.BOOTSTRAP_ENABLED and not company_exists)}

@router.post("/register-company", response_model=TokenResponse)
def register_company(
    request: CompanyRegisterRequest,
    db: Session = Depends(get_db),
    setup_token: str | None = Header(default=None, alias="X-Setup-Token"),
):
    """First-time company registration flow creating company, default roles, starter departments, and admin account."""
    if not settings.BOOTSTRAP_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company setup is not enabled.")
    if not setup_token or not settings.BOOTSTRAP_TOKEN or not secrets.compare_digest(setup_token, settings.BOOTSTRAP_TOKEN):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="A valid setup token is required.")
    if db.query(Company.id).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Company setup has already been completed.")

    existing_user = db.query(User).filter(User.email == request.admin_email.strip().lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    # 1. Create Company
    company = Company(
        name=request.company_name.strip(),
        industry=request.industry.strip(),
        description=f"Private workspace for {request.company_name.strip()}",
        settings={"domain": request.domain.strip() if request.domain else "", "industry": request.industry.strip()}
    )
    db.add(company)
    db.commit()
    db.refresh(company)

    # 2. Create Standard Roles
    role_admin = Role(
        company_id=company.id,
        name="Administrator",
        code="ADMIN",
        description="Full organization management and administrative authority.",
        permissions=DEFAULT_ROLE_PERMISSIONS["ADMIN"],
        clearance_level=4
    )
    role_manager = Role(
        company_id=company.id,
        name="Manager",
        code="MANAGER",
        description="Team supervision, task delegation, and approval review.",
        permissions=DEFAULT_ROLE_PERMISSIONS["MANAGER"],
        clearance_level=3
    )
    role_employee = Role(
        company_id=company.id,
        name="Team Member",
        code="EMPLOYEE",
        description="Standard team associate access.",
        permissions=DEFAULT_ROLE_PERMISSIONS["EMPLOYEE"],
        clearance_level=1
    )
    db.add_all([role_admin, role_manager, role_employee])
    db.commit()
    db.refresh(role_admin)

    # 3. Create Industry-Specific Starter Departments
    industry_lower = request.industry.lower()
    dept_templates = [
        ("Operations", "OPS", "Operations and team coordination."),
        ("Product & Strategy", "PROD", "Product management, planning, and strategy."),
        ("General Administration", "ADMIN", "General organization administration.")
    ]
    if "photo" in industry_lower:
        dept_templates = [
            ("Photography", "PHOTO", "Photo shoots, studio sessions, and capture."),
            ("Editing", "EDIT", "Post-processing, color grading, and asset delivery."),
            ("Client Relations", "CLIENT", "Client bookings, inquiries, and reviews.")
        ]
    elif "tech" in industry_lower or "software" in industry_lower:
        dept_templates = [
            ("Engineering", "ENG", "Software engineering and technical architecture."),
            ("Design", "DESIGN", "Product design and user experience."),
            ("Marketing", "MKTG", "Growth, outreach, and user communication.")
        ]
    elif "manufactur" in industry_lower:
        dept_templates = [
            ("Production", "PROD", "Fabrication, assembly, and plant operations."),
            ("Quality", "QC", "Quality assurance, inspections, and compliance."),
            ("Maintenance", "MAINT", "Equipment maintenance and calibration.")
        ]
    elif "food" in industry_lower:
        dept_templates = [
            ("Production", "PROD", "Kitchen operations and food preparation."),
            ("Quality & Safety", "QC", "Food safety, hygiene, and standards compliance."),
            ("Sales", "SALES", "Customer service, orders, and retail sales.")
        ]
    elif "finance" in industry_lower:
        dept_templates = [
            ("Finance & Accounting", "FIN", "Budgeting, accounting, and cash flow."),
            ("Operations", "OPS", "Compliance, transaction management, and execution."),
            ("Client Services", "CLIENT", "Client advisory and account management.")
        ]

    created_depts = []
    for d_name, d_code, d_desc in dept_templates:
        d = Department(company_id=company.id, name=d_name, code=d_code, description=d_desc)
        db.add(d)
        created_depts.append(d)
    db.commit()
    for d in created_depts:
        db.refresh(d)

    # 4. Create Admin Account
    admin_user = User(
        company_id=company.id,
        department_id=created_depts[0].id if created_depts else None,
        role_id=role_admin.id,
        email=request.admin_email.strip().lower(),
        full_name=request.admin_name.strip(),
        job_title="Workspace Owner & Administrator",
        employee_code="ADM-001",
        hashed_password=hash_password(request.password),
        clearance_level=4,
        is_admin=True,
        is_active=True
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)

    # 5. Audit Log
    record_audit_event(
        db=db,
        company_id=company.id,
        action="COMPANY_REGISTERED",
        resource_type="COMPANY",
        resource_id=company.id,
        user=admin_user,
        details={"company_name": company.name, "industry": company.industry, "admin": admin_user.email}
    )

    token = create_access_token(
        subject=admin_user.id,
        data={"email": admin_user.email, "company_id": admin_user.company_id, "clearance": admin_user.clearance_level}
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(admin_user)
    )

@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    normalized_email = request.email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive account.")

    token = create_access_token(
        subject=user.id,
        data={"email": user.email, "company_id": user.company_id, "clearance": user.clearance_level}
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)

if settings.DEMO_MODE:
    @router.post("/demo-switch/{role_code}", response_model=TokenResponse)
    def switch_demo_role(role_code: str, db: Session = Depends(get_db)):
        """Issues a demo identity only in an explicitly enabled demo environment."""
        role_code_upper = role_code.strip().upper()
    
        email_map = {
        # NovaWorks Team Members
        "SAUMY": "saumy@novaworks.com",
        "SOUMYA": "saumy@novaworks.com",
        "ASHUTOSH": "ashutosh@novaworks.com",
        "HETVI": "hetvi@novaworks.com",
        "ARYA": "arya@novaworks.com",
        "JIDNYASA": "jidnyasa@novaworks.com",
        "JIGNASA": "jidnyasa@novaworks.com",
        "KRISH": "krish@novaworks.com",
        
        # Generic Roles & Aliases
        "ADMIN": "saumy@novaworks.com",
        "DIRECTOR": "saumy@novaworks.com",
        "MANAGER": "ashutosh@novaworks.com",
        "LEAD_ENGINEER": "ashutosh@novaworks.com",
        "CREATIVE": "ashutosh@novaworks.com",
        "FINANCE": "hetvi@novaworks.com",
        "QC_SUPERVISOR": "hetvi@novaworks.com",
        "QC": "hetvi@novaworks.com",
        "TECHNICIAN": "arya@novaworks.com",
        "SPECIALIST": "arya@novaworks.com",
        "CNC_TECH": "arya@novaworks.com",
        "OPERATIONS": "jidnyasa@novaworks.com",
        "EMPLOYEE": "krish@novaworks.com",
        "OPERATOR": "krish@novaworks.com",
        "SAFETY_OFFICER": "krish@novaworks.com",
        "SAFETY": "krish@novaworks.com"
        }

        target_email = email_map.get(role_code_upper)
        if not target_email:
            raise HTTPException(status_code=404, detail="Unknown demo identity.")
        user = db.query(User).filter(User.email == target_email, User.is_active == True).first()
        if not user:
            raise HTTPException(status_code=404, detail="Demo identity not found.")

        token = create_access_token(
            subject=user.id,
            data={"email": user.email, "company_id": user.company_id, "clearance": user.clearance_level}
        )

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse.model_validate(user)
        )
