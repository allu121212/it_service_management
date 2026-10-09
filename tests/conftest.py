import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app import models
from app.main import app

# In-memory SQLite for fast tests
TEST_DB_URL = "sqlite:///./test_it_service.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()

    # Seed minimal data
    db.add_all([
        models.Priority(name="Critical", sla_hours=4),
        models.Priority(name="High",     sla_hours=8),
        models.Priority(name="Medium",   sla_hours=24),
        models.Priority(name="Low",      sla_hours=48),
    ])
    db.add_all([
        models.Category(name="Hardware"),
        models.Category(name="Software"),
        models.Category(name="Network"),
        models.Category(name="Email"),
    ])
    db.add_all([
        models.User(name="Alice", email="alice@corp.com", role="employee"),
        models.User(name="Bob",   email="bob@corp.com",   role="employee"),
        models.User(name="Charlie IT", email="charlie@corp.com", role="it_staff"),
    ])
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    return TestClient(app)