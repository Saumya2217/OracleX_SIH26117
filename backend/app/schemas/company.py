from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel
from datetime import datetime

class DepartmentCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None

class DepartmentDeleteResponse(BaseModel):
    status: Literal["success"]
    deleted_id: str

class RoleCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    permissions: List[str] = []
    clearance_level: int = 1

class CompanyResponse(BaseModel):
    id: str
    name: str
    industry: str
    description: Optional[str] = None
    mission_statement: Optional[str] = None
    compliance_standards: List[str] = []
    settings: Dict[str, Any] = {}
    created_at: datetime

    class Config:
        from_attributes = True

class HierarchyNode(BaseModel):
    id: str
    name: str
    title: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    clearance_level: int = 1
    subordinates: List["HierarchyNode"] = []

HierarchyNode.model_rebuild()
