from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
import pytest

from app.auth import create_access_token, get_auth_settings, require_team_member
from app.database import Settings, get_db
from app.main import app
from app.models import User
from app.set_role import set_role


@pytest.fixture
def settings():
    return Settings(_env_file=None, google_client_id="test-client-id",
                    auth_secret_key="test-secret-key-at-least-32-characters")


@pytest.fixture
def client(db, settings):
    test_app = FastAPI()
    test_app.exception_handlers.update(app.exception_handlers)

    @test_app.get("/team-only")
    def team_only(user: Annotated[User, Depends(require_team_member)]):
        return {"id": str(user.id)}

    test_app.dependency_overrides[get_db] = lambda: db
    test_app.dependency_overrides[get_auth_settings] = lambda: settings
    with TestClient(test_app) as test_client:
        yield test_client


@pytest.fixture
def student(db):
    user = User(id=uuid4(), google_sub="team-test", email="Student@Example.com",
                name="Test Student", role="student")
    db.add(user)
    db.commit()
    return user


@pytest.mark.parametrize("role,status", [("team_member", 200), ("student", 403)])
def test_team_member_authorization(client, db, settings, student, role, status):
    token = create_access_token(student.id, settings)
    student.role = role
    db.commit()
    response = client.get("/team-only", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == status
    if status == 403:
        assert response.json()["error"] == {
            "code": "FORBIDDEN", "message": "Team member access is required.", "details": [],
        }
    else:
        assert response.json() == {"id": str(student.id)}


def test_team_member_requires_token(client):
    response = client.get("/team-only")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


@pytest.mark.parametrize("email", ["Student@Example.com", "STUDENT@example.COM"])
def test_set_role_promotes_student(db, student, email):
    assert set_role(db, email, "team_member") == 1
    db.flush()
    db.refresh(student)
    assert student.role == "team_member"


def test_set_role_unknown_email(db, student):
    assert set_role(db, "unknown@example.com", "team_member") == 0
    db.refresh(student)
    assert student.role == "student"


def test_set_role_rejects_invalid_role(db, student):
    with pytest.raises(ValueError, match="student or team_member"):
        set_role(db, student.email, "admin")
    db.refresh(student)
    assert student.role == "student"
