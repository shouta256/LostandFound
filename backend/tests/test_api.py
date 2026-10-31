from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth import create_access_token, get_auth_settings
from app.database import Settings, get_db
from app.main import app
from app.models import Item, User
from app.seed import seed_items


@pytest.fixture
def authenticated_api(db):
    user = User(
        id=uuid4(), google_sub=f"api-user-{uuid4()}",
        email="api-user@example.com", name="API Student", role="student",
    )
    db.add(user)
    db.commit()
    settings = Settings(
        _env_file=None,
        google_client_id="test-client-id",
        auth_secret_key="test-secret-key-at-least-32-characters",
    )
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_auth_settings] = lambda: settings
    token = create_access_token(user.id, settings)
    try:
        with TestClient(app) as client:
            yield client, db, user, {"Authorization": f"Bearer {token}"}
    finally:
        app.dependency_overrides.clear()


def test_get_items_reads_seeded_database(db):
    seed_items(db)
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/items")
        assert response.status_code == 200
        page = response.json()
        assert page["total"] == 5
        assert len(page["data"]) == 5
        assert page["data"][0]["name"] == "Gray hoodie"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "params, expected_names",
    [
        ({"type": "found"}, {"Blue backpack", "Red backpack", "Small pouch", "Gray hoodie"}),
        ({"category": "bags"}, {"Blue backpack", "Red backpack", "Green backpack"}),
        ({"category": "  bags  "}, {"Blue backpack", "Red backpack", "Green backpack"}),
        ({"category": "Bag"}, {"Small pouch"}),
        ({"category": "Ba"}, set()),
        ({"type": "found", "category": "bags", "q": "library"}, {"Blue backpack"}),
        ({"type": "found", "category": "bags", "limit": 1}, {"Blue backpack", "Red backpack"}),
    ],
)
def test_get_items_filters_before_pagination(authenticated_api, params, expected_names):
    client, db, user, _headers = authenticated_api
    now = datetime.now(timezone.utc)
    for item_type, name, category, description, status in [
        ("found", "Blue backpack", "Bags", "Found in library", "available"),
        ("found", "Red backpack", "Bags", "Found in gym", "available"),
        ("lost", "Green backpack", "Bags", "Lost in library", "available"),
        ("found", "Small pouch", "Bag", "Found in library", "available"),
        ("found", "Gray hoodie", "Clothing", "Found in library", "available"),
        ("found", "Returned backpack", "Bags", "Found in library", "returned"),
    ]:
        db.add(Item(
            id=uuid4(), type=item_type, name=name, description=description,
            category=category, date=date(2026, 10, 20), location="Student center",
            status=status, created_by=user.id, created_at=now, updated_at=now,
        ))
    db.commit()

    response = client.get("/api/v1/items", params=params)

    assert response.status_code == 200
    page = response.json()
    assert page["total"] == len(expected_names)
    assert len(page["data"]) == min(len(expected_names), params.get("limit", 20))
    assert {item["name"] for item in page["data"]} <= expected_names


@pytest.mark.parametrize("params", [
    {"type": "other"},
    {"category": ""},
    {"category": "   "},
    {"category": "a" * 81},
])
def test_get_items_rejects_invalid_filters(authenticated_api, params):
    client, _db, _user, _headers = authenticated_api

    response = client.get("/api/v1/items", params=params)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_item_sets_owner_status_and_location(authenticated_api):
    client, db, user, headers = authenticated_api
    response = client.post(
        "/api/v1/items",
        headers=headers,
        json={
            "type": "found",
            "name": "  Gray hoodie  ",
            "description": "Found near the library",
            "category": "Clothing",
            "date": "2026-10-28",
            "location": "Library entrance",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert response.headers["location"] == f"/api/v1/items/{body['id']}"
    assert body["name"] == "Gray hoodie"
    assert body["status"] == "available"
    assert body["created_by"] == str(user.id)
    assert body["date"] == "2026-10-28"
    saved_item = db.get(Item, UUID(body["id"]))
    assert saved_item is not None
    assert saved_item.created_by == user.id


def test_create_item_rejects_invalid_date_and_blank_text(authenticated_api):
    client, db, _user, headers = authenticated_api
    body = {
        "type": "lost",
        "name": "   ",
        "description": "Item description",
        "category": "Other",
        "date": "2026-1-2",
        "location": "Main hall",
    }

    response = client.post("/api/v1/items", headers=headers, json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert db.scalar(select(Item.id)) is None


def test_get_item_returns_requested_item_including_returned_items(authenticated_api):
    client, db, user, headers = authenticated_api
    now = datetime.now(timezone.utc)
    item = Item(
        id=uuid4(), type="found", name="Returned wallet", description="Brown leather wallet",
        category="Accessories", date=date(2026, 10, 20), location="Student center",
        status="returned", created_by=user.id, created_at=now, updated_at=now,
    )
    db.add(item)
    db.commit()

    response = client.get(f"/api/v1/items/{item.id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == str(item.id)
    assert response.json()["status"] == "returned"


def test_get_item_returns_not_found_for_unknown_id(authenticated_api):
    client, _db, _user, headers = authenticated_api

    response = client.get(f"/api/v1/items/{uuid4()}", headers=headers)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ITEM_NOT_FOUND"
