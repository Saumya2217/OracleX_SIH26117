import os
import shutil
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

TEST_RUNTIME_DIR = tempfile.mkdtemp(prefix="oraclex-tests-")
os.environ["SECRET_KEY"] = "test-only-secret-key-with-at-least-32-characters"
os.environ["TESTING"] = "true"
os.environ["DEMO_MODE"] = "false"
os.environ["BOOTSTRAP_ENABLED"] = "true"
os.environ["BOOTSTRAP_TOKEN"] = "test-bootstrap-token-12345"
os.environ["SIMULATED_AI_FALLBACK"] = "true"
os.environ["CHROMA_PERSIST_DIR"] = os.path.join(TEST_RUNTIME_DIR, "chroma")
os.environ["CHROMA_HOST"] = ""
os.environ["UPLOAD_DIR"] = os.path.join(TEST_RUNTIME_DIR, "uploads")
os.environ["OLLAMA_BASE_URL"] = "http://127.0.0.1:9"
os.environ["INGESTION_INLINE_FOR_TESTS"] = "true"

from app.database import Base, get_db
from app.main import app
from app.core.seed_data import seed_database
from app.services.vector_store import vector_store_service

# Use in-memory SQLite database for test isolation
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        vector_store_service.client.delete_collection("oraclex_company_knowledge")
    except Exception:
        pass
    vector_store_service.collection = vector_store_service.client.get_or_create_collection(
        name="oraclex_company_knowledge",
        embedding_function=vector_store_service.embedding_fn
    )
    seed_database(db, force_reseed=True)
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)
    shutil.rmtree(TEST_RUNTIME_DIR, ignore_errors=True)

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def empty_client():
    empty_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    empty_session_local = sessionmaker(autocommit=False, autoflush=False, bind=empty_engine)
    Base.metadata.create_all(bind=empty_engine)
    db = empty_session_local()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(bind=empty_engine)
        empty_engine.dispose()


@pytest.fixture
def auth_headers(client):
    def login(email: str):
        response = client.post("/api/auth/login", json={
            "email": email,
            "password": "password123",
        })
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return login
