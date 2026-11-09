from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models.company import Department, User
from app.models.workflow import Workflow, Task
from app.schemas.workflow import (
    WorkflowResponse, TaskResponse, TaskCreate, TaskUpdate,
)
from app.api.deps import get_current_user
from app.services.audit_service import record_audit_event
from app.core.permissions import PermissionScope, user_has_permission

router = APIRouter(prefix="/workflows", tags=["Workflows & Action Hub"])

@router.get("/", response_model=List[WorkflowResponse])
def list_workflows(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    wfs = db.query(Workflow).filter(Workflow.company_id == current_user.company_id).all()
    return [WorkflowResponse.model_validate(w) for w in wfs]

# Tasks
@router.get("/tasks", response_model=List[TaskResponse])
def list_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Task).filter(Task.company_id == current_user.company_id)
    if not user_has_permission(current_user, PermissionScope.TASK_MANAGE):
        query = query.filter(or_(Task.assigned_to_id == current_user.id, Task.created_by_id == current_user.id))
    tasks = query.all()
    results = []
    for t in tasks:
        resp = TaskResponse.model_validate(t)
        if t.assigned_to:
            resp.assigned_to_name = t.assigned_to.full_name
        results.append(resp)
    return results

@router.post("/tasks", response_model=TaskResponse)
def create_task(
    task_in: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not user_has_permission(current_user, PermissionScope.TASK_CREATE):
        raise HTTPException(status_code=403, detail="Task creation permission required.")

    assigned_to_id = task_in.assigned_to_id or current_user.id
    if assigned_to_id != current_user.id and not user_has_permission(current_user, PermissionScope.TASK_ASSIGN):
        raise HTTPException(status_code=403, detail="Task assignment permission required.")
    assignee = db.query(User).filter(
        User.id == assigned_to_id,
        User.company_id == current_user.company_id,
        User.is_active == True,
    ).first()
    if not assignee:
        raise HTTPException(status_code=422, detail="Assignee is not an active user in this company.")

    department_id = task_in.department_id or current_user.department_id
    if department_id and not db.query(Department.id).filter(
        Department.id == department_id,
        Department.company_id == current_user.company_id,
    ).first():
        raise HTTPException(status_code=422, detail="Department is not part of this company.")

    task = Task(
        company_id=current_user.company_id,
        department_id=department_id,
        assigned_to_id=assigned_to_id,
        created_by_id=current_user.id,
        title=task_in.title,
        description=task_in.description,
        project_name=task_in.project_name,
        priority=task_in.priority,
        status=task_in.status
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    record_audit_event(
        db=db,
        company_id=current_user.company_id,
        action="TASK_CREATE",
        resource_type="TASK",
        resource_id=task.id,
        user=current_user,
        details={"title": task.title, "priority": task.priority}
    )

    resp = TaskResponse.model_validate(task)
    if task.assigned_to:
        resp.assigned_to_name = task.assigned_to.full_name
    return resp

@router.patch("/tasks/{task_id}", response_model=TaskResponse)
def update_task_status(
    task_id: str,
    update_in: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id, Task.company_id == current_user.company_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    can_manage = user_has_permission(current_user, PermissionScope.TASK_MANAGE)
    if task.assigned_to_id != current_user.id and task.created_by_id != current_user.id and not can_manage:
        raise HTTPException(status_code=403, detail="You cannot modify this task.")

    if update_in.status:
        task.status = update_in.status
    if update_in.priority:
        task.priority = update_in.priority
    if update_in.assigned_to_id:
        if update_in.assigned_to_id != task.assigned_to_id and not user_has_permission(current_user, PermissionScope.TASK_ASSIGN):
            raise HTTPException(status_code=403, detail="Task assignment permission required.")
        assignee = db.query(User).filter(
            User.id == update_in.assigned_to_id,
            User.company_id == current_user.company_id,
            User.is_active == True,
        ).first()
        if not assignee:
            raise HTTPException(status_code=422, detail="Assignee is not an active user in this company.")
        task.assigned_to_id = update_in.assigned_to_id

    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)

    record_audit_event(
        db=db,
        company_id=current_user.company_id,
        action="TASK_UPDATE",
        resource_type="TASK",
        resource_id=task.id,
        user=current_user,
        details={"status": task.status, "priority": task.priority}
    )

    resp = TaskResponse.model_validate(task)
    if task.assigned_to:
        resp.assigned_to_name = task.assigned_to.full_name
    return resp
