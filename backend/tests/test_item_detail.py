"""Item detail checks on SQLite and PostgreSQL with disposable transactions."""

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from backend.app.models import Item, User
from backend.app.items import create_items_router, error_response
from backend.app.database import get_db
from backend.tests.test_item_creation import api  # noqa: F401


@pytest.mark.parametrize("item_type,status", [
    ("lost", "available"), ("lost", "returned"), ("found", "available"),
    ("found", "claimed"), ("found", "returned"),
])
@pytest.mark.parametrize("role", ["student", "team_member"])
def test_item_detail_for_another_users_listing(api, item_type, status, role):
    client, session, requester = api
    session.get(User, requester).role = role
    creator = User(google_sub=f"detail-{uuid4()}", email="creator@example.com")
    timestamp = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    item = Item(
        creator=creator, type=item_type, name="Blue Bottle", description="Blue  strap",
        category="Other", date=date(2026, 1, 1), location="Library", status=status,
        created_at=timestamp, updated_at=timestamp,
    )
    session.add(item)
    session.flush()
    identifier = item.id
    owner = creator.id
    # Force retrieval from storage rather than the existing identity-map object.
    session.expunge(item)
    response = client.get(f"/api/v1/items/{identifier}")
    assert response.status_code == 200, response.text
    assert response.json() == {
        "id": str(identifier), "type": item_type, "name": "Blue Bottle",
        "description": "Blue  strap", "category": "Other", "date": "2026-01-01",
        "location": "Library", "status": status, "created_by": str(owner),
        "created_at": "2026-01-02T03:04:05Z", "updated_at": "2026-01-02T03:04:05Z",
    }


def test_missing_item(api):
    client, _, _ = api
    response = client.get(f"/api/v1/items/{uuid4()}")
    assert response.status_code == 404
    assert response.json() == {"error": {
        "code": "ITEM_NOT_FOUND", "message": "Item not found.", "details": [],
    }}


@pytest.mark.parametrize("identifier", ["not-a-uuid", "123", "g" * 32, "00000000-0000-0000-0000-00000000000x"])
def test_invalid_uuid_does_not_query_database(api, identifier, monkeypatch):
    client, session, _ = api

    def unexpected_query(*args, **kwargs):
        pytest.fail("Invalid UUID must be rejected before database lookup")

    monkeypatch.setattr(session, "get", unexpected_query)
    response = client.get(f"/api/v1/items/{identifier}")
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"] == [{"field": "path.item_id", "message": "Must be a valid UUID"}]


def test_database_error(api, monkeypatch):
    client, session, _ = api

    def fail(*args, **kwargs):
        raise SQLAlchemyError("private connection details")

    monkeypatch.setattr(session, "get", fail)
    response = client.get(f"/api/v1/items/{uuid4()}")
    assert response.status_code == 500
    assert response.json() == {"error": {
        "code": "INTERNAL_ERROR", "message": "Unable to retrieve item.", "details": [],
    }}


@pytest.mark.parametrize("status,code", [(401, "UNAUTHENTICATED"), (403, "FORBIDDEN")])
def test_injected_authentication_can_deny_access(api, monkeypatch, status, code):
    _, session, _ = api

    def deny():
        raise HTTPException(status_code=status, detail=code)

    # The host application owns authentication and its contract error handling.
    async def handle_authentication(request, exc):
        response = error_response(exc.status_code, exc.detail, "Access denied.")
        if exc.status_code == 401:
            response.headers["WWW-Authenticate"] = "Bearer"
        return response

    def unexpected_query(*args, **kwargs):
        pytest.fail("Authentication must deny access before item lookup")

    app = FastAPI()
    app.include_router(create_items_router(deny))
    app.dependency_overrides[get_db] = lambda: session
    app.add_exception_handler(HTTPException, handle_authentication)
    monkeypatch.setattr(session, "get", unexpected_query)
    with TestClient(app) as client:
        response = client.get(f"/api/v1/items/{uuid4()}")
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    if status == 401:
        assert response.headers["WWW-Authenticate"] == "Bearer"
