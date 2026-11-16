import sys
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add backend directory to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.database import Base, get_db
from app.main import app
from app.inter_service.identity_client import generate_mock_token

# In-memory SQLite engine with StaticPool so all connections share the same in-memory DB
TEST_DATABASE_URL = "sqlite://"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def owner_headers():
    token = generate_mock_token("CIT-OWNER-001")
    return {"Authorization": f"Bearer {token}", "X-Correlation-ID": "test-corr-owner-001"}

@pytest.fixture
def renter_headers():
    token = generate_mock_token("CIT-RENTER-002")
    return {"Authorization": f"Bearer {token}", "X-Correlation-ID": "test-corr-renter-002"}

@pytest.fixture
def low_kyc_renter_headers():
    token = generate_mock_token("CIT-RENTER-LOWKYC")
    return {"Authorization": f"Bearer {token}", "X-Correlation-ID": "test-corr-lowkyc-003"}

@pytest.fixture
def admin_headers():
    token = generate_mock_token("CIT-ADMIN-001")
    return {"Authorization": f"Bearer {token}", "X-Correlation-ID": "test-corr-admin-001"}
