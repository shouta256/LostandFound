from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.auth import create_access_token, get_auth_settings
from app.database import Settings, get_db
from app.main import app
from app.models import Claim, Item, Pickup, User


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
    team = User(
        id=uuid4(), google_sub=f"team-{uuid4()}",
        email="team@example.com", name="Team", role="team_member",
    )
    db.add_all([claimant, owner, team])
    db.commit()

    settings = Settings(
        _env_file=None,
        google_client_id="test-client-id",
        auth_secret_key="test-secret-key-at-least-32-characters",
    )
    token = create_access_token(claimant.id, settings)
    team_token = create_access_token(team.id, settings)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_auth_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            yield client, db, claimant, owner, {"Authorization": f"Bearer {token}"}, team, {"Authorization": f"Bearer {team_token}"}
    finally:
        app.dependency_overrides.clear()


def add_item(db, owner, *, type="found", status="available"):
    now = datetime.now(timezone.utc)
    item = Item(
        id=uuid4(), type=type, name="Blue backpack", description="A blue backpack",
        category="Bags", date=date(2026, 11, 1), location="Library",
        status=status, created_by=owner.id, created_at=now, updated_at=now,
    )
    db.add(item)
    db.commit()
    return item


def test_create_claim_persists_authenticated_claimant_and_returns_201(claims_api):
    client, db, claimant, owner, headers, _team, _team_headers = claims_api
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
    client, db, claimant, _owner, headers, _team, _team_headers = claims_api
    item = add_item(db, claimant)

    response = client.post(
        "/api/v1/claims", headers=headers,
        json={"item_id": str(item.id), "ownership_information": "I recognize it."},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    assert db.scalar(select(Claim.id)) is None


def test_create_claim_rejects_second_pending_claim(claims_api):
    client, db, claimant, owner, headers, _team, _team_headers = claims_api
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
    client, db, _claimant, _owner, headers, _team, _team_headers = claims_api

    response = client.post("/api/v1/claims", headers=headers, json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert db.scalar(select(Claim.id)) is None


def test_create_claim_rejects_missing_or_unavailable_item(claims_api):
    client, db, _claimant, owner, headers, _team, _team_headers = claims_api
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


def add_claim(db, item, claimant):
    now = datetime.now(timezone.utc)
    claim = Claim(
        id=uuid4(), item_id=item.id, claimant_id=claimant.id,
        ownership_information="A small tear by the left pocket.", status="pending",
        reviewed_by=None, reviewed_at=None, created_at=now, updated_at=now,
    )
    db.add(claim)
    db.commit()
    return claim


def test_create_claim_rejects_lost_item(claims_api):
    client, db, _claimant, owner, headers, _team, _team_headers = claims_api
    item = add_item(db, owner, type="lost")

    response = client.post("/api/v1/claims", headers=headers, json={
        "item_id": str(item.id), "ownership_information": "Details.",
    })

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ITEM_NOT_CLAIMABLE"
    assert db.scalar(select(Claim.id)) is None


def test_approval_claims_item_and_blocks_other_pending_claim(claims_api):
    client, db, claimant, owner, headers, team, team_headers = claims_api
    item = add_item(db, owner)
    claim = add_claim(db, item, claimant)
    other = add_claim(db, item, owner)

    response = client.patch(f"/api/v1/claims/{claim.id}/decision", headers=team_headers,
                            json={"status": "approved"})

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["reviewed_by"] == str(team.id)
    assert response.json()["reviewed_at"] is not None
    db.refresh(claim)
    db.refresh(item)
    assert claim.status == "approved"
    assert claim.reviewed_by == team.id
    assert claim.reviewed_at is not None
    assert item.status == "claimed"
    assert client.get(f"/api/v1/claims/{claim.id}", headers=headers).json()["pickup"] is None

    conflict = client.patch(f"/api/v1/claims/{other.id}/decision", headers=team_headers,
                            json={"status": "approved"})
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "CLAIM_APPROVAL_CONFLICT"
    db.refresh(other)
    assert other.status == "pending"
    assert other.reviewed_by is None
    assert other.reviewed_at is None


def test_approval_rejects_legacy_pending_claim_on_lost_item(claims_api):
    client, db, claimant, owner, _headers, _team, team_headers = claims_api
    item = add_item(db, owner, type="lost")
    claim = add_claim(db, item, claimant)

    response = client.patch(f"/api/v1/claims/{claim.id}/decision", headers=team_headers,
                            json={"status": "approved"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CLAIM_APPROVAL_CONFLICT"
    db.refresh(claim)
    db.refresh(item)
    assert claim.status == "pending"
    assert claim.reviewed_at is None
    assert item.status == "available"


@pytest.mark.parametrize("type", ["found", "lost"])
def test_rejection_is_idempotent_and_leaves_item_available(claims_api, type):
    client, db, claimant, owner, _headers, team, team_headers = claims_api
    item = add_item(db, owner, type=type)
    claim = add_claim(db, item, claimant)
    original_updated_at = item.updated_at
    url = f"/api/v1/claims/{claim.id}/decision"

    first = client.patch(url, headers=team_headers, json={"status": "rejected"})
    repeat = client.patch(url, headers=team_headers, json={"status": "rejected"})
    opposite = client.patch(url, headers=team_headers, json={"status": "approved"})

    assert first.status_code == repeat.status_code == 200
    assert first.json()["status"] == "rejected"
    assert first.json()["reviewed_by"] == str(team.id)
    assert first.json()["reviewed_at"] is not None
    assert repeat.json() == first.json()
    assert opposite.status_code == 409
    assert opposite.json()["error"]["code"] == "CLAIM_ALREADY_DECIDED"
    db.refresh(item)
    assert item.status == "available"
    assert item.updated_at == original_updated_at


def test_team_member_cannot_review_own_claim(claims_api):
    client, db, _claimant, owner, _headers, team, team_headers = claims_api
    item = add_item(db, owner)
    claim = add_claim(db, item, team)

    response = client.patch(f"/api/v1/claims/{claim.id}/decision", headers=team_headers,
                            json={"status": "approved"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    db.refresh(claim)
    assert claim.status == "pending"


@pytest.mark.parametrize("operation", ["decision", "pickup", "status"])
def test_students_cannot_change_team_workflow(claims_api, operation):
    client, db, claimant, owner, headers, _team, _team_headers = claims_api
    item = add_item(db, owner)
    claim = add_claim(db, item, claimant)
    url, body = {
        "decision": (f"/claims/{claim.id}/decision", {"status": "approved"}),
        "pickup": (f"/claims/{claim.id}/pickup", {"location": "Library", "status": "ready"}),
        "status": (f"/items/{item.id}/status", {"status": "returned"}),
    }[operation]

    response = client.patch(f"/api/v1{url}", headers=headers, json=body)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    db.refresh(claim)
    db.refresh(item)
    assert claim.status == "pending"
    assert item.status == "available"
    assert db.get(Pickup, claim.id) is None


@pytest.mark.parametrize("type,current,target,expected", [
    ("found", "available", "returned", 409),
    ("found", "available", "claimed", 409),
    ("found", "claimed", "returned", 200),
    ("lost", "available", "returned", 200),
    ("lost", "available", "claimed", 409),
    ("found", "claimed", "available", 409),
    ("found", "returned", "claimed", 409),
    ("lost", "returned", "available", 409),
])
def test_type_specific_status_transitions(claims_api, type, current, target, expected):
    client, db, _claimant, owner, _headers, _team, team_headers = claims_api
    item = add_item(db, owner, type=type, status=current)
    original_updated_at = item.updated_at

    response = client.patch(f"/api/v1/items/{item.id}/status", headers=team_headers,
                            json={"status": target})

    assert response.status_code == expected
    db.refresh(item)
    assert item.status == (target if expected == 200 else current)
    if expected == 409:
        assert response.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"
        assert item.updated_at == original_updated_at


@pytest.mark.parametrize("type,status", [
    ("found", "available"), ("found", "claimed"), ("found", "returned"),
    ("lost", "available"), ("lost", "returned"),
])
def test_same_status_preserves_updated_at(claims_api, type, status):
    client, db, _claimant, owner, _headers, _team, team_headers = claims_api
    item = add_item(db, owner, type=type, status=status)
    original_updated_at = item.updated_at

    for _ in range(2):
        response = client.patch(f"/api/v1/items/{item.id}/status", headers=team_headers,
                                json={"status": status})
        assert response.status_code == 200
        assert datetime.fromisoformat(response.json()["updated_at"]) == original_updated_at
    db.refresh(item)
    assert item.updated_at == original_updated_at


def test_pickup_readiness_preserves_and_clears_ready_at(claims_api):
    client, db, claimant, owner, _headers, _team, team_headers = claims_api
    item = add_item(db, owner)
    claim = add_claim(db, item, claimant)
    url = f"/api/v1/claims/{claim.id}/pickup"
    body = {"location": "Library", "status": "ready"}

    pending = client.patch(url, headers=team_headers, json=body)
    assert pending.status_code == 409
    assert pending.json()["error"]["code"] == "CLAIM_NOT_APPROVED"
    assert db.get(Pickup, claim.id) is None
    approved = client.patch(f"/api/v1/claims/{claim.id}/decision", headers=team_headers,
                            json={"status": "approved"})
    assert approved.status_code == 200

    ready = client.patch(url, headers=team_headers, json=body)
    assert ready.status_code == 200
    assert ready.json()["ready_at"] is not None
    repeat = client.patch(url, headers=team_headers, json={**body, "location": "Front desk"})
    assert repeat.status_code == 200
    assert repeat.json()["location"] == "Front desk"
    assert repeat.json()["ready_at"] == ready.json()["ready_at"]
    not_ready = client.patch(url, headers=team_headers, json={**body, "status": "not_ready"})
    assert not_ready.status_code == 200
    assert not_ready.json()["ready_at"] is None
    db.refresh(db.get(Pickup, claim.id))
    assert db.get(Pickup, claim.id).ready_at is None


def test_student_claim_reads_are_private_and_pending_pickup_is_null(claims_api):
    client, db, claimant, owner, headers, _team, _team_headers = claims_api
    item = add_item(db, owner)
    own = add_claim(db, item, claimant)
    other = add_claim(db, item, owner)

    response = client.get("/api/v1/claims", headers=headers)
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert [claim["id"] for claim in response.json()["data"]] == [str(own.id)]
    detail = client.get(f"/api/v1/claims/{own.id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["pickup"] is None
    forbidden = client.get(f"/api/v1/claims/{other.id}", headers=headers)
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "FORBIDDEN"

def test_create_claim_allows_new_claim_after_rejection(claims_api):  # TC-US8-05
    client, db, claimant, owner, headers, team, _team_headers = claims_api
    item = add_item(db, owner)
    team_id = team.id
    old = add_claim(db, item, claimant)
    old.reviewed_by = team_id
    old.reviewed_at = datetime.now(timezone.utc)
    old.status = "rejected"
    db.commit()

    response = client.post(
        "/api/v1/claims", headers=headers,
        json={"item_id": str(item.id), "ownership_information": "New details."},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "pending"


def test_create_claim_rejects_details_over_2000_chars(claims_api):  # TC-US8-10
    client, db, _claimant, owner, headers, _team, _team_headers = claims_api
    item = add_item(db, owner)

    response = client.post(
        "/api/v1/claims", headers=headers,
        json={"item_id": str(item.id), "ownership_information": "a" * 2001},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert db.scalar(select(Claim.id)) is None


def test_create_claim_accepts_details_at_2000_chars(claims_api):  # TC-US8-11
    client, db, _claimant, owner, headers, _team, _team_headers = claims_api
    item = add_item(db, owner)

    response = client.post(
        "/api/v1/claims", headers=headers,
        json={"item_id": str(item.id), "ownership_information": "a" * 2000},
    )

    assert response.status_code == 201


def test_create_claim_requires_login(claims_api):  # TC-US8-12
    client, db, _claimant, owner, _headers, _team, _team_headers = claims_api
    item = add_item(db, owner)

    response = client.post(
        "/api/v1/claims",
        json={"item_id": str(item.id), "ownership_information": "Details."},
    )

    assert response.status_code == 401
    assert db.scalar(select(Claim.id)) is None