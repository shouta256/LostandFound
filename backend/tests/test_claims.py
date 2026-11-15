from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.auth import create_access_token, get_auth_settings
from app.database import Settings, get_db
from app.main import app
from app.models import Claim, Item, User


@pytest.fixture
def claims_api(db):
    claimant = User(
        id=uuid4(), google_sub=f"claimant-{uuid4()}",
        email="claimant@example.com", name="Claimant", role="student",
    )
    owner = User(
        id=uuid4(), google_sub=f"owner-{uuid4()}",
        email="owner@example.com", name="Owner", role="student",
    )
    db.add_all([claimant, owner])
    db.commit()

    settings = Settings(
        _env_file=None,
        google_client_id="test-client-id",
        auth_secret_key="test-secret-key-at-least-32-characters",
    )
    token = create_access_token(claimant.id, settings)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_auth_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            yield client, db, claimant, owner, {"Authorization": f"Bearer {token}"}
    finally:
        app.dependency_overrides.clear()


def add_item(db, owner, *, status="available"):
    now = datetime.now(timezone.utc)
    item = Item(
        id=uuid4(), type="found", name="Blue backpack", description="A blue backpack",
        category="Bags", date=date(2026, 11, 1), location="Library",
        status=status, created_by=owner.id, created_at=now, updated_at=now,
    )
    db.add(item)
    db.commit()
    return item


def test_create_claim_persists_authenticated_claimant_and_returns_201(claims_api):
    client, db, claimant, owner, headers = claims_api
    item = add_item(db, owner)

    response = client.post(
        "/api/v1/claims", headers=headers,
        json={"item_id": str(item.id), "ownership_information": "  A small tear by the left pocket.  "},
    )

    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert response.headers["location"] == f"/api/v1/claims/{body['id']}"
    assert body["item_id"] == str(item.id)
    assert body["claimant_id"] == str(claimant.id)
    assert body["ownership_information"] == "A small tear by the left pocket."
    assert body["status"] == "pending"
    assert body["reviewed_by"] is None
    assert body["reviewed_at"] is None

    saved = db.get(Claim, body["id"])
    assert saved is not None
    assert saved.claimant_id == claimant.id
    assert saved.item_id == item.id
    assert saved.ownership_information == "A small tear by the left pocket."


def test_create_claim_rejects_own_listing(claims_api):
    client, db, claimant, _owner, headers = claims_api
    item = add_item(db, claimant)

    response = client.post(
        "/api/v1/claims", headers=headers,
        json={"item_id": str(item.id), "ownership_information": "I recognize it."},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    assert db.scalar(select(Claim.id)) is None


def test_create_claim_rejects_second_pending_claim(claims_api):
    client, db, claimant, owner, headers = claims_api
    item = add_item(db, owner)
    first = client.post(
        "/api/v1/claims", headers=headers,
        json={"item_id": str(item.id), "ownership_information": "First detail."},
    )
    assert first.status_code == 201

    duplicate = client.post(
        "/api/v1/claims", headers=headers,
        json={"item_id": str(item.id), "ownership_information": "Second detail."},
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DUPLICATE_PENDING_CLAIM"
    assert db.scalar(select(func.count()).select_from(Claim).where(Claim.item_id == item.id)) == 1


@pytest.mark.parametrize("body", [
    {"item_id": "not-a-uuid", "ownership_information": "Details."},
    {"item_id": str(uuid4()), "ownership_information": "   "},
    {"item_id": str(uuid4()), "ownership_information": "Details.", "claimant_id": str(uuid4())},
])
def test_create_claim_rejects_invalid_request_body(claims_api, body):
    client, db, _claimant, _owner, headers = claims_api

    response = client.post("/api/v1/claims", headers=headers, json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert db.scalar(select(Claim.id)) is None


def test_create_claim_rejects_missing_or_unavailable_item(claims_api):
    client, db, _claimant, owner, headers = claims_api
    missing = client.post(
        "/api/v1/claims", headers=headers,
        json={"item_id": str(uuid4()), "ownership_information": "Details."},
    )
    unavailable_item = add_item(db, owner, status="returned")
    unavailable = client.post(
        "/api/v1/claims", headers=headers,
        json={"item_id": str(unavailable_item.id), "ownership_information": "Details."},
    )

    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "ITEM_NOT_FOUND"
    assert unavailable.status_code == 409
    assert unavailable.json()["error"]["code"] == "ITEM_NOT_CLAIMABLE"
    assert db.scalar(select(Claim.id)) is None
