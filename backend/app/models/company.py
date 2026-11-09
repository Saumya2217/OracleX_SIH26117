import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, Boolean, JSON
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Company(Base):
    __tablename__ = "companies"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    industry = Column(String(100), nullable=False, default="Manufacturing")
    description = Column(Text, nullable=True)
    mission_statement = Column(Text, nullable=True)
    compliance_standards = Column(JSON, default=list)  # e.g. ["ISO9001", "AS9100D", "ITAR"]
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    departments = relationship("Department", back_populates="company", cascade="all, delete-orphan")
    roles = relationship("Role", back_populates="company", cascade="all, delete-orphan")
    users = relationship("User", back_populates="company", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="company", cascade="all, delete-orphan")
    workflows = relationship("Workflow", back_populates="company", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="company", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="company", cascade="all, delete-orphan")


class Department(Base):
    __tablename__ = "departments"

    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(150), nullable=False)
    code = Column(String(50), nullable=False)  # e.g. "ENG", "QC", "OPS"
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="departments")
    users = relationship("User", back_populates="department")
    documents = relationship("Document", back_populates="department")


class Role(Base):
    __tablename__ = "roles"

    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)  # e.g. "Director", "Lead Engineer", "Floor Technician"
    code = Column(String(50), nullable=False)  # e.g. "ADMIN", "MANAGER", "EMPLOYEE", "TECH"
    description = Column(Text, nullable=True)
    permissions = Column(JSON, default=list)  # ["doc:read", "doc:upload", "workflow:approve", etc.]
    clearance_level = Column(Integer, default=1)  # 1: Public, 2: Internal, 3: Confidential, 4: Restricted
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="roles")
    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    department_id = Column(String, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    role_id = Column(String, ForeignKey("roles.id", ondelete="SET NULL"), nullable=True)
    reports_to_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    employee_code = Column(String(50), nullable=True)
    job_title = Column(String(150), nullable=True)
    clearance_level = Column(Integer, default=1)  # 1 to 4
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="users")
    department = relationship("Department", back_populates="users")
    role = relationship("Role", back_populates="users")
    reports_to = relationship("User", remote_side=[id], backref="subordinates")
    tasks = relationship("Task", back_populates="assigned_to", foreign_keys="Task.assigned_to_id")
