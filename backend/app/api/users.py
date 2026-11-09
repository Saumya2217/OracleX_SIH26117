from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.company import Department, Role, User
from app.schemas.auth import UserResponse, UserCreateRequest, UserUpdateRequest
from app.api.deps import get_current_user, require_admin
from app.core.security import hash_password
from app.services.audit_service import record_audit_event

router = APIRouter(prefix="/users", tags=["Users & Personnel"])


def _validate_company_relationships(
    db: Session,
    company_id: str,
    department_id: Optional[str],
    role_id: Optional[str],
    reports_to_id: Optional[str],
    subject_id: Optional[str] = None,
):
    if department_id and not db.query(Department.id).filter(
        Department.id == department_id, Department.company_id == company_id
    ).first():
        raise HTTPException(status_code=422, detail="Department is not part of this company.")
    if role_id and not db.query(Role.id).filter(
        Role.id == role_id, Role.company_id == company_id
    ).first():
        raise HTTPException(status_code=422, detail="Role is not part of this company.")
    if reports_to_id:
        if subject_id and reports_to_id == subject_id:
            raise HTTPException(status_code=422, detail="A user cannot report to themselves.")
        if not db.query(User.id).filter(
            User.id == reports_to_id,
            User.company_id == company_id,
            User.is_active == True,
        ).first():
            raise HTTPException(status_code=422, detail="Supervisor is not an active user in this company.")


def _ensure_another_active_admin(db: Session, user: User):
    if not user.is_admin or not user.is_active:
        return
    other_admin_exists = db.query(User.id).filter(
        User.company_id == user.company_id,
        User.is_admin == True,
        User.is_active == True,
        User.id != user.id,
    ).first()
    if not other_admin_exists:
        raise HTTPException(status_code=409, detail="The company must retain at least one active administrator.")

@router.get("/", response_model=List[UserResponse])
def list_company_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    users = db.query(User).filter(User.company_id == current_user.company_id).all()
    return [UserResponse.model_validate(u) for u in users]

@router.get("/{user_id}", response_model=UserResponse)
def get_user_detail(user_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id, User.company_id == current_user.company_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return UserResponse.model_validate(user)

@router.post("/", response_model=UserResponse)
def create_employee(
    request: UserCreateRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    normalized_email = request.email.strip().lower()
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists.")

    _validate_company_relationships(
        db,
        admin_user.company_id,
        request.department_id,
        request.role_id,
        request.reports_to_id,
    )

    new_user = User(
        company_id=admin_user.company_id,
        email=normalized_email,
        full_name=request.full_name.strip(),
        hashed_password=hash_password(request.password),
        employee_code=request.employee_code,
        job_title=request.job_title,
        clearance_level=request.clearance_level,
        department_id=request.department_id,
        role_id=request.role_id,
        reports_to_id=request.reports_to_id,
        is_admin=request.is_admin
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    record_audit_event(
        db=db,
        company_id=admin_user.company_id,
        action="USER_CREATED",
        resource_type="USER",
        resource_id=new_user.id,
        user=admin_user,
        details={"email": new_user.email, "is_admin": new_user.is_admin},
    )
    return UserResponse.model_validate(new_user)

@router.put("/{user_id}", response_model=UserResponse)
def update_employee(
    user_id: str,
    request: UserUpdateRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id, User.company_id == admin_user.company_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    _validate_company_relationships(
        db,
        admin_user.company_id,
        request.department_id if "department_id" in request.model_fields_set else None,
        request.role_id if "role_id" in request.model_fields_set else None,
        request.reports_to_id if "reports_to_id" in request.model_fields_set else None,
        subject_id=user.id,
    )

    removes_final_admin = (
        (request.is_admin is False)
        or (request.is_active is False)
    )
    if removes_final_admin:
        _ensure_another_active_admin(db, user)

    if request.full_name is not None:
        user.full_name = request.full_name
    if request.employee_code is not None:
        user.employee_code = request.employee_code
    if request.job_title is not None:
        user.job_title = request.job_title
    if request.clearance_level is not None:
        user.clearance_level = request.clearance_level
    if "department_id" in request.model_fields_set:
        user.department_id = request.department_id
    if "role_id" in request.model_fields_set:
        user.role_id = request.role_id
    if "reports_to_id" in request.model_fields_set:
        user.reports_to_id = request.reports_to_id
    if request.is_admin is not None:
        user.is_admin = request.is_admin
    if request.is_active is not None:
        user.is_active = request.is_active

    db.commit()
    db.refresh(user)
    record_audit_event(
        db=db,
        company_id=admin_user.company_id,
        action="USER_UPDATED",
        resource_type="USER",
        resource_id=user.id,
        user=admin_user,
        details={"fields": sorted(request.model_fields_set)},
    )
    return UserResponse.model_validate(user)

@router.patch("/{user_id}/status", response_model=UserResponse)
def toggle_user_status(
    user_id: str,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id, User.company_id == admin_user.company_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.is_active:
        _ensure_another_active_admin(db, user)
    
    # Toggle active status
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    record_audit_event(
        db=db,
        company_id=admin_user.company_id,
        action="USER_STATUS_CHANGED",
        resource_type="USER",
        resource_id=user.id,
        user=admin_user,
        details={"is_active": user.is_active},
    )
    return UserResponse.model_validate(user)

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    user_id: str,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id, User.company_id == admin_user.company_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.id == admin_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete current active administrator.")
    _ensure_another_active_admin(db, user)

    deleted_email = user.email
    db.delete(user)
    db.commit()
    record_audit_event(
        db=db,
        company_id=admin_user.company_id,
        action="USER_DELETED",
        resource_type="USER",
        resource_id=user_id,
        user=admin_user,
        details={"email": deleted_email},
    )
    return None
