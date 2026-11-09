from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.company import Company, Department, Role, User
from app.models.knowledge import Document
from app.models.workflow import Task, Workflow
from app.schemas.company import CompanyResponse, HierarchyNode, DepartmentCreate, DepartmentUpdate, DepartmentDeleteResponse
from app.schemas.auth import DepartmentResponse, RoleResponse
from app.api.deps import get_current_user, require_admin
from app.core.seed_data import seed_database
from app.config import settings

router = APIRouter(prefix="/company", tags=["Company & Organization"])

@router.get("/profile", response_model=CompanyResponse)
def get_company_profile(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")
    return CompanyResponse.model_validate(company)

@router.get("/departments", response_model=List[DepartmentResponse])
def get_departments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    depts = db.query(Department).filter(Department.company_id == current_user.company_id).all()
    return [DepartmentResponse.model_validate(d) for d in depts]

@router.post("/departments", response_model=DepartmentResponse)
def create_department(dept_in: DepartmentCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    dept = Department(
        company_id=current_user.company_id,
        name=dept_in.name.strip(),
        code=dept_in.code.strip().upper(),
        description=dept_in.description
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return DepartmentResponse.model_validate(dept)

@router.put("/departments/{dept_id}", response_model=DepartmentResponse)
def update_department(dept_id: str, dept_in: DepartmentUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    dept = db.query(Department).filter(Department.id == dept_id, Department.company_id == current_user.company_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found.")
    if dept_in.name:
        dept.name = dept_in.name.strip()
    if dept_in.code:
        dept.code = dept_in.code.strip().upper()
    if dept_in.description is not None:
        dept.description = dept_in.description
    db.commit()
    db.refresh(dept)
    return DepartmentResponse.model_validate(dept)

@router.delete("/departments/{dept_id}", response_model=DepartmentDeleteResponse)
def delete_department(dept_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    dept = db.query(Department).filter(Department.id == dept_id, Department.company_id == current_user.company_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found.")
    dependencies = (
        db.query(User.id).filter(User.company_id == current_user.company_id, User.department_id == dept_id).first()
        or db.query(Document.id).filter(Document.company_id == current_user.company_id, Document.department_id == dept_id).first()
        or db.query(Task.id).filter(Task.company_id == current_user.company_id, Task.department_id == dept_id).first()
        or db.query(Workflow.id).filter(Workflow.company_id == current_user.company_id, Workflow.department_id == dept_id).first()
    )
    if dependencies:
        raise HTTPException(status_code=409, detail="This team is still referenced by people, documents, tasks, or workflows.")
    db.delete(dept)
    db.commit()
    return {"status": "success", "deleted_id": dept_id}


@router.get("/roles", response_model=List[RoleResponse])
def get_roles(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    roles = db.query(Role).filter(Role.company_id == current_user.company_id).all()
    return [RoleResponse.model_validate(r) for r in roles]

@router.get("/hierarchy", response_model=HierarchyNode)
def get_org_hierarchy(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Constructs the organizational reporting tree rooted at the top executive."""
    users = db.query(User).filter(User.company_id == current_user.company_id, User.is_active == True).all()
    
    user_map = {}
    for u in users:
        dept_name = u.department.name if u.department else "General"
        role_name = u.role.name if u.role else "Member"
        user_map[u.id] = {
            "id": u.id,
            "name": u.full_name,
            "title": u.job_title,
            "role": role_name,
            "department": dept_name,
            "clearance_level": u.clearance_level or 1,
            "reports_to_id": u.reports_to_id,
            "subordinates": []
        }

    # Find root (user with no reports_to_id or director)
    roots = []
    for uid, udata in user_map.items():
        parent_id = udata["reports_to_id"]
        if parent_id and parent_id in user_map:
            user_map[parent_id]["subordinates"].append(udata)
        else:
            roots.append(udata)

    def convert_to_node(node_dict: dict) -> HierarchyNode:
        return HierarchyNode(
            id=node_dict["id"],
            name=node_dict["name"],
            title=node_dict["title"],
            role=node_dict["role"],
            department=node_dict["department"],
            clearance_level=node_dict["clearance_level"],
            subordinates=[convert_to_node(child) for child in node_dict["subordinates"]]
        )

    root_dict = roots[0] if roots else (list(user_map.values())[0] if user_map else {
        "id": "root", "name": "Company Root", "title": "Director", "role": "ADMIN",
        "department": "EXEC", "clearance_level": 4, "subordinates": []
    })

    return convert_to_node(root_dict)

if settings.DEMO_MODE:
    @router.post("/seed")
    def trigger_seed(
        db: Session = Depends(get_db),
        current_user: User = Depends(require_admin),
    ):
        """Creates demo fixtures only in an explicitly enabled demo environment."""
        comp = seed_database(db)
        return {"status": "success", "company_id": comp.id, "name": comp.name}
