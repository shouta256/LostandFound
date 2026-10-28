"""Status API tests on SQLite and PostgreSQL with disposable transactions."""

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from backend.app.models import Claim, Item, User
from backend.app.database import get_db
from backend.app.items import create_items_router, error_response
from backend.tests.test_item_creation import api  # noqa: F401


@pytest.fixture
def status_api(api):
    client, session, user_id = api
    session.get(User, user_id).role = "team_member"
    session.flush()
    if session.bind.dialect.name == "sqlite":
        Claim.__table__.create(session.connection())
    return client, session, user_id


def make_item(session, owner, kind="found", status="available"):
    original = datetime(2020, 1, 1, tzinfo=timezone.utc)
    item = Item(
        type=kind, status=status, name="Bottle", description="Blue bottle",
        category="Other", date=date(2026, 10, 28), location="Library",
        created_by=owner, created_at=original, updated_at=original,
    )
    session.add(item)
    session.flush()
    return item


def add_claim(session, item, reviewer, status="approved"):
    claimant = User(google_sub=f"status-{uuid4()}", email="claimant@example.com")
    claim = Claim(item=item, claimant=claimant, ownership_information="Blue strap", status=status)
    if status != "pending":
        claim.reviewed_by = reviewer
        claim.reviewed_at = datetime.now(timezone.utc)
    session.add(claim)
    session.flush()
    return claim


@pytest.mark.parametrize("kind,before,after", [
    ("lost", "available", "returned"), ("found", "available", "claimed"),
    ("found", "claimed", "returned"),
])
def test_valid_transition(status_api, kind, before, after):
    client, session, owner = status_api
    item = make_item(session, owner, kind, before)
    claim = add_claim(session, item, owner) if kind == "found" else None
    claim_id = claim.id if claim else None
    identifier = item.id
    response = client.patch(f"/api/v1/items/{identifier}/status", json={"status": after})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == str(identifier) and body["status"] == after
    assert body["created_at"] == "2020-01-01T00:00:00Z"
    assert body["updated_at"] != body["created_at"]
    session.expire_all()
    assert session.get(Item, identifier).status == after
    if claim:
        assert session.get(Claim, claim_id).status == "approved"


@pytest.mark.parametrize("kind,before,after", [
    ("found", "available", "returned"), ("found", "claimed", "available"),
    ("found", "returned", "available"), ("found", "returned", "claimed"),
    ("lost", "available", "claimed"), ("lost", "returned", "available"),
    ("lost", "returned", "claimed"),
])
def test_invalid_transition(status_api, kind, before, after):
    client, session, owner = status_api
    item = make_item(session, owner, kind, before)
    response = client.patch(f"/api/v1/items/{item.id}/status", json={"status": after})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"
    session.refresh(item)
    assert item.status == before


@pytest.mark.parametrize("claim_status", [None, "pending", "rejected"])
def test_claimed_requires_approved_claim(status_api, claim_status):
    client, session, owner = status_api
    item = make_item(session, owner)
    if claim_status:
        add_claim(session, item, owner, claim_status)
    response = client.patch(f"/api/v1/items/{item.id}/status", json={"status": "claimed"})
    assert response.status_code == 409


@pytest.mark.parametrize("kind,status", [
    ("lost", "available"), ("lost", "returned"), ("found", "available"),
    ("found", "claimed"), ("found", "returned"),
])
def test_repeated_status_preserves_timestamps(status_api, kind, status):
    client, session, owner = status_api
    item = make_item(session, owner, kind, status)
    claim = add_claim(session, item, owner) if status == "claimed" else None
    review_time = claim.reviewed_at if claim else None
    response = client.patch(f"/api/v1/items/{item.id}/status", json={"status": status})
    assert response.status_code == 200
    assert response.json()["updated_at"] == "2020-01-01T00:00:00Z"
    assert response.json()["created_at"] == response.json()["updated_at"]
    if claim:
        assert claim.reviewed_at.replace(tzinfo=timezone.utc) == review_time
        assert claim.reviewed_by == owner


def test_student_cannot_update_even_own_listing(api):
    client, session, owner = api
    item = make_item(session, owner, "lost")
    response = client.patch(f"/api/v1/items/{item.id}/status", json={"status": "returned"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    session.refresh(item)
    assert item.status == "available"


@pytest.mark.parametrize("payload", [{}, {"status": None}, {"status": "other"},
    {"status": "returned", "name": "changed"}, [], {"status": 1}])
def test_invalid_payload(status_api, payload):
    client, _, _ = status_api
    response = client.patch(f"/api/v1/items/{uuid4()}/status", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_identifier_and_body_errors(status_api):
    client, _, _ = status_api
    response = client.patch("/api/v1/items/not-a-uuid/status", json={"status": "returned"})
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "path.item_id"
    path = f"/api/v1/items/{uuid4()}/status"
    response = client.patch(path, json={"status": "returned"})
    assert response.status_code == 404 and response.json()["error"]["code"] == "ITEM_NOT_FOUND"
    response = client.patch(path, content="{", headers={"Content-Type": "application/json"})
    assert response.status_code == 400 and response.json()["error"]["code"] == "INVALID_JSON"
    response = client.patch(path, content="text", headers={"Content-Type": "text/plain"})
    assert response.status_code == 415 and response.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


@pytest.mark.parametrize("failure", ["scalar", "flush", "commit"])
def test_database_error_and_rollback(status_api, monkeypatch, failure):
    client, session, owner = status_api
    item = make_item(session, owner, "lost")
    identifier = item.id
    rolled_back = []
    rollback = session.rollback

    def fail(*args, **kwargs):
        raise SQLAlchemyError("private database details")

    def track_rollback():
        rolled_back.append(True)
        rollback()

    monkeypatch.setattr(session, failure, fail)
    monkeypatch.setattr(session, "rollback", track_rollback)
    response = client.patch(f"/api/v1/items/{identifier}/status", json={"status": "returned"})
    assert response.status_code == 500
    assert response.json() == {"error": {
        "code": "INTERNAL_ERROR", "message": "Unable to update item status.", "details": [],
    }}
    assert rolled_back == [True]


def test_unauthenticated_request_is_denied(api):
    _, session, _ = api

    def deny():
        raise HTTPException(status_code=401, detail="UNAUTHENTICATED")

    async def handle_authentication(request, exc):
        response = error_response(401, exc.detail, "Authentication required.")
        response.headers["WWW-Authenticate"] = "Bearer"
        return response

    app = FastAPI()
    app.include_router(create_items_router(deny))
    app.dependency_overrides[get_db] = lambda: session
    app.add_exception_handler(HTTPException, handle_authentication)
    with TestClient(app) as client:
        response = client.patch(f"/api/v1/items/{uuid4()}/status", json={"status": "returned"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"
    assert response.headers["WWW-Authenticate"] == "Bearer"
