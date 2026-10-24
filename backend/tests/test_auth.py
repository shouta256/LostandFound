from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from google.auth.exceptions import GoogleAuthError, TransportError
import jwt
import pytest
from sqlalchemy import func, select

from app.auth import get_auth_settings, get_current_user
from app.database import Settings, get_db
from app.errors import APIError
from app.main import app
from app.models import User


@pytest.fixture
def auth_settings():
    return Settings(_env_file=None, google_client_id="test-client-id",
                    auth_secret_key="test-secret-key-at-least-32-characters")


@pytest.fixture
def client(db, auth_settings):
    # Exercise the shared dependency without implementing the teammate's /users/me.
    test_app = FastAPI()
    test_app.include_router(app.router)
    test_app.exception_handlers.update(app.exception_handlers)

    @test_app.get("/protected")
    def protected(user: Annotated[User, Depends(get_current_user)]):
        return {"id": str(user.id), "role": user.role}

    test_app.dependency_overrides[get_db] = lambda: db
    test_app.dependency_overrides[get_auth_settings] = lambda: auth_settings
    with TestClient(test_app) as test_client:
        yield test_client


@pytest.fixture
def google_verify(monkeypatch):
    from unittest.mock import Mock

    verifier = Mock(return_value={
        "sub": "google-user-123", "email": "student@example.com",
        "email_verified": True, "name": "Test Student",
    })
    monkeypatch.setattr("app.auth.id_token.verify_oauth2_token", verifier)
    return verifier


def test_login_creates_user_and_issues_one_hour_token(client, db, google_verify, auth_settings):
    response = client.post("/api/v1/auth/google", json={"id_token": "google-token"})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] == 3600
    assert set(body["user"]) == {"id", "email", "name", "role"}
    assert body["user"]["role"] == "student"
    assert body["user"]["email"] == "student@example.com"
    user = db.scalar(select(User))
    assert str(user.id) == body["user"]["id"]
    assert user.google_sub == "google-user-123"
    claims = jwt.decode(body["access_token"], auth_settings.auth_secret_key.get_secret_value(),
                        algorithms=["HS256"], issuer="lostandfound")
    assert claims["exp"] - claims["iat"] == 3600
    assert claims["sub"] == str(user.id)
    assert "role" not in claims
    assert google_verify.call_args.kwargs["audience"] == "test-client-id"
    protected = client.get("/protected", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert protected.json() == {"id": str(user.id), "role": "student"}
    # Permissions must come from the current database record, not a stale token.
    user.role = "team_member"
    db.commit()
    assert client.get("/protected", headers={"Authorization": f"Bearer {body['access_token']}"}).json()["role"] == "team_member"


def test_repeat_login_preserves_identity_and_assigned_role(client, db, google_verify):
    first = client.post("/api/v1/auth/google", json={"id_token": "google-token"}).json()
    user = db.scalar(select(User))
    user.role = "team_member"
    db.commit()
    google_verify.return_value.update(email="updated@example.com", name=None)
    second = client.post("/api/v1/auth/google", json={"id_token": "google-token"}).json()
    assert second["user"]["id"] == first["user"]["id"]
    assert second["user"]["role"] == "team_member"
    assert second["user"]["email"] == "updated@example.com"
    assert second["user"]["name"] is None
    assert db.scalar(select(func.count()).select_from(User)) == 1


@pytest.mark.parametrize("error,status,code", [
    (ValueError("private token data"), 401, "INVALID_GOOGLE_TOKEN"),
    (GoogleAuthError("invalid issuer"), 401, "INVALID_GOOGLE_TOKEN"),
    (TransportError("network unavailable"), 503, "AUTH_PROVIDER_UNAVAILABLE"),
])
def test_google_verification_errors(client, db, google_verify, error, status, code):
    google_verify.side_effect = error
    response = client.post("/api/v1/auth/google", json={"id_token": "google-token"})
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert response.headers["cache-control"] == "no-store"
    assert "private token data" not in response.text
    assert db.scalar(select(func.count()).select_from(User)) == 0


def test_unverified_email_is_rejected(client, db, google_verify):
    google_verify.return_value["email_verified"] = False
    response = client.post("/api/v1/auth/google", json={"id_token": "google-token"})
    assert response.status_code == 401
    assert db.scalar(select(func.count()).select_from(User)) == 0


@pytest.mark.parametrize("body", [{}, {"id_token": ""}, {"id_token": "token", "role": "team_member"}])
def test_login_validates_body(client, google_verify, body):
    response = client.post("/api/v1/auth/google", json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    google_verify.assert_not_called()


def test_login_rejects_malformed_json_and_wrong_content_type(client, google_verify):
    malformed = client.post("/api/v1/auth/google", content="{", headers={"Content-Type": "application/json"})
    assert malformed.status_code == 400
    assert malformed.json()["error"]["code"] == "INVALID_JSON"
    unsupported = client.post("/api/v1/auth/google", content="id_token=token",
                              headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert unsupported.status_code == 415
    assert unsupported.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"
    google_verify.assert_not_called()


@pytest.mark.parametrize("kind", ["missing", "wrong_scheme", "tampered", "expired", "unknown_user", "missing_exp", "wrong_issuer"])
def test_protected_dependency_rejects_invalid_credentials(client, db, auth_settings, kind):
    user = User(id=uuid4(), google_sub="test-user", email="student@example.com", role="student")
    db.add(user)
    db.commit()
    now = datetime.now(timezone.utc)
    claims = {"sub": str(user.id), "iss": "lostandfound", "iat": now, "exp": now + timedelta(hours=1)}
    key = auth_settings.auth_secret_key.get_secret_value()
    valid_token = jwt.encode(claims, key, algorithm="HS256")
    assert client.get("/protected", headers={"Authorization": f"Bearer {valid_token}"}).status_code == 200
    # Change only the condition under test; keep the user valid.
    if kind == "expired":
        claims["exp"] = now - timedelta(seconds=1)
    elif kind == "missing_exp":
        del claims["exp"]
    elif kind == "wrong_issuer":
        claims["iss"] = "another-app"
    elif kind == "unknown_user":
        claims["sub"] = str(uuid4())
    elif kind == "tampered":
        key = "wrong-key-that-is-at-least-32-characters"
    token = jwt.encode(claims, key, algorithm="HS256")
    headers = {} if kind == "missing" else {"Authorization": f"{'Basic' if kind == 'wrong_scheme' else 'Bearer'} {token}"}
    response = client.get("/protected", headers=headers)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_missing_auth_configuration_fails_closed(monkeypatch):
    monkeypatch.setattr("app.auth.Settings", lambda: Settings(_env_file=None, google_client_id="", auth_secret_key=""))
    with pytest.raises(APIError) as error:
        get_auth_settings()
    assert error.value.status_code == 500
