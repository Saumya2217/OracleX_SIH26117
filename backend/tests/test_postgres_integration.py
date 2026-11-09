import os
import threading
from datetime import datetime
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.company import Company, Department, Role, User
from app.models.knowledge import Document
from app.models.workflow import Workflow, Task, ApprovalRequest
from app.models.audit import AuditLog
from app.models.request import BusinessRequest
from app.core.seed_data import seed_database
from app.core.security import verify_password, create_access_token, decode_access_token
from app.services.audit_service import record_audit_event
from app.services.request_service import create_request_draft

POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL", "postgresql://oraclex_user:oraclex_secure_password@127.0.0.1:5432/oraclex_db")

@pytest.fixture(scope="module")
def pg_session():
    """Provides a PostgreSQL session for integration testing."""
    try:
        engine = create_engine(POSTGRES_TEST_URL)
        with engine.connect() as conn:
            pass
    except Exception as e:
        pytest.skip(f"PostgreSQL not reachable at {POSTGRES_TEST_URL}: {e}")
    
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    try:
        seed_database(db, force_reseed=False)
        yield db
    finally:
        db.close()

def test_pg_company_and_org_structure(pg_session):
    company = pg_session.query(Company).first()
    assert company is not None
    assert "NovaWorks" in company.name
    
    depts = pg_session.query(Department).filter(Department.company_id == company.id).all()
    assert len(depts) >= 4
    
    roles = pg_session.query(Role).filter(Role.company_id == company.id).all()
    assert len(roles) >= 4

def test_pg_users_and_authentication(pg_session):
    users = pg_session.query(User).all()
    assert len(users) >= 6
    
    admin = pg_session.query(User).filter(User.email == "saumy@novaworks.com").first()
    assert admin is not None
    assert verify_password("password123", admin.hashed_password)
    
    token = create_access_token(admin.id, {"email": admin.email, "role": "ADMIN"})
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == admin.id
    assert payload["email"] == "saumy@novaworks.com"

def test_pg_documents_and_clearance(pg_session):
    docs = pg_session.query(Document).all()
    assert len(docs) >= 6
    clearance_levels = {d.clearance_level for d in docs}
    assert 1 in clearance_levels  # PUBLIC
    assert 2 in clearance_levels  # INTERNAL
    assert 3 in clearance_levels  # CONFIDENTIAL
    assert 4 in clearance_levels  # RESTRICTED

def test_pg_workflows_and_audit(pg_session):
    wfs = pg_session.query(Workflow).all()
    assert len(wfs) >= 2
    
    company = pg_session.query(Company).first()
    admin = pg_session.query(User).filter(User.email == "saumy@novaworks.com").first()
    
    log = record_audit_event(
        db=pg_session,
        company_id=company.id,
        action="INTEGRATION_TEST_EXECUTION",
        resource_type="SYSTEM",
        user=admin,
        details={"suite": "PostgreSQL Integration"},
        status="SUCCESS"
    )
    assert log.integrity_hash is not None
    expected = AuditLog.calculate_hash({
        "company_id": log.company_id,
        "user_id": log.user_id,
        "action": log.action,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
        "details": log.details or {},
        "status": log.status
    })
    assert log.integrity_hash == expected


def test_pg_only_one_simultaneous_request_decision_wins(pg_session):
    requester = pg_session.query(User).filter(User.email == "arya@novaworks.com").one()
    request = create_request_draft(
        pg_session,
        requester=requester,
        request_type="ACCESS_REQUEST",
        title="PostgreSQL concurrency probe",
        description="Disposable request used to verify decision serialization.",
        risk_level="MEDIUM",
        payload={
            "resource": "concurrency-test-resource",
            "access_level": "VIEW",
            "business_reason": "Verify that exactly one simultaneous reviewer decision commits.",
        },
    )
    request.status = "SUBMITTED"
    request.submitted_version_id = request.current_version_id
    request.lock_version = 2
    pg_session.commit()
    request_id = request.id
    submitted_version_id = request.submitted_version_id

    Session = sessionmaker(autocommit=False, autoflush=False, bind=pg_session.get_bind())
    barrier = threading.Barrier(2)
    results: list[int] = []
    result_lock = threading.Lock()

    def decide(status: str):
        session = Session()
        try:
            barrier.wait(timeout=5)
            updated = session.query(BusinessRequest).filter(
                BusinessRequest.id == request_id,
                BusinessRequest.lock_version == 2,
                BusinessRequest.status == "SUBMITTED",
                BusinessRequest.submitted_version_id == submitted_version_id,
            ).update({
                BusinessRequest.status: status,
                BusinessRequest.decision: status,
                BusinessRequest.lock_version: 3,
                BusinessRequest.updated_at: datetime.utcnow(),
            }, synchronize_session=False)
            session.commit()
            with result_lock:
                results.append(updated)
        finally:
            session.close()

    first = threading.Thread(target=decide, args=("APPROVED",))
    second = threading.Thread(target=decide, args=("REJECTED",))
    first.start()
    second.start()
    first.join(timeout=10)
    second.join(timeout=10)

    assert sorted(results) == [0, 1]
    pg_session.expire_all()
    decided = pg_session.get(BusinessRequest, request_id)
    assert decided.status in {"APPROVED", "REJECTED"}
    assert decided.lock_version == 3
