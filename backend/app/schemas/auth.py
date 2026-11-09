from typing import Optional, List, Any
from pydantic import BaseModel, Field
from datetime import datetime

class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=1024)

class BootstrapStatusResponse(BaseModel):
    enabled: bool

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"

class RoleResponse(BaseModel):
    id: str
    name: str
    code: str
    description: Optional[str] = None
    permissions: List[str] = []
    clearance_level: int = 1

    class Config:
        from_attributes = True

class DepartmentResponse(BaseModel):
    id: str
    name: str
    code: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    id: str
    company_id: str
    email: str
    full_name: str
    employee_code: Optional[str] = None
    job_title: Optional[str] = None
    clearance_level: int = 1
    is_admin: bool = False
    is_active: bool = True
    department_id: Optional[str] = None
    role_id: Optional[str] = None
    reports_to_id: Optional[str] = None
    department: Optional[DepartmentResponse] = None
    role: Optional[RoleResponse] = None
    created_at: datetime

    class Config:
        from_attributes = True

class UserCreateRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=12, max_length=1024)
    employee_code: Optional[str] = None
    job_title: Optional[str] = None
    clearance_level: int = Field(default=1, ge=1, le=4)
    department_id: Optional[str] = None
    role_id: Optional[str] = None
    reports_to_id: Optional[str] = None
    is_admin: bool = False

class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    employee_code: Optional[str] = None
    job_title: Optional[str] = None
    clearance_level: Optional[int] = Field(default=None, ge=1, le=4)
    department_id: Optional[str] = None
    role_id: Optional[str] = None
    reports_to_id: Optional[str] = None
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None

class CompanyRegisterRequest(BaseModel):
    admin_name: str = Field(min_length=2, max_length=255)
    company_name: str = Field(min_length=2, max_length=255)
    industry: str = Field(min_length=2, max_length=255)
    domain: Optional[str] = Field(default=None, max_length=255)
    admin_email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=12, max_length=1024)

TokenResponse.model_rebuild()
