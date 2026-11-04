import os
import sys
from pathlib import Path
from types import SimpleNamespace

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "migration-test-secret"
os.environ["GEMINI_API_KEY"] = "migration-test-key"
os.environ["VERCEL"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.main import app
from app.database import Base, get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.resume import Resume
from app.api.endpoints.interviews import get_interview_service


@pytest.fixture
def database():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([User(id=1, email="one@example.com", hashed_password="unused"),
                    User(id=2, email="two@example.com", hashed_password="unused")])
        db.commit()
        yield db
    engine.dispose()


@pytest.fixture
def client(database):
    app.dependency_overrides[get_db] = lambda: database
    app.dependency_overrides[get_current_user] = lambda: database.get(User, 1)
    with TestClient(app, base_url="https://testserver") as client:
        yield client
    app.dependency_overrides.clear()


def test_upload_survives_a_new_database_session(client, database):
    pdf = b"%PDF-1.4 candidate one"
    response = client.post("/resumeupload", files={"resume": ("resume.pdf", pdf, "application/pdf")})
    assert response.status_code == 200
    with Session(database.bind) as other_instance:
        assert other_instance.get(Resume, 1).content == pdf
        assert other_instance.get(Resume, 2) is None
    replacement = b"%PDF-1.4 updated"
    assert client.post("/resumeupload", files={"resume": ("resume.pdf", replacement)}).status_code == 200
    assert database.get(Resume, 1).content == replacement


def test_rejects_invalid_and_oversized_uploads(client, database):
    assert client.post("/resumeupload", files={"resume": ("bad.pdf", b"not pdf")}).status_code == 400
    assert client.post("/resumeupload", files={"resume": ("large.pdf", b"%PDF-" + b"x" * (4 * 1024 * 1024))}).status_code == 413
    assert database.get(Resume, 1) is None


def test_candidate_context_is_restored_and_isolated(database):
    database.add_all([Resume(user_id=1, content=b"%PDF-one"), Resume(user_id=2, content=b"%PDF-two")])
    database.commit()
    request = SimpleNamespace(app=app)
    one = get_interview_service(request, database.get(User, 1), database)
    two = get_interview_service(request, database.get(User, 2), database)
    restarted = get_interview_service(request, database.get(User, 1), database)
    assert one is not two and one is not restarted
    assert one.uploaded_resume_file.inline_data.data == b"%PDF-one"
    assert two.uploaded_resume_file.inline_data.data == b"%PDF-two"
    assert restarted.uploaded_resume_file.inline_data.data == b"%PDF-one"


def test_health_and_auth_routes_are_api_responses(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.post("/login", json={}).status_code == 422
