"""Listing tests run on SQLite and opt-in PostgreSQL with rolled-back data."""

from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from backend.app.models import Item, User
from backend.tests.test_item_creation import api  # noqa: F401


@pytest.fixture
def listings(api):
    client, session, owner = api
    marker = str(uuid4())
    other = User(google_sub=f"listing-{marker}", email="other@example.com")
    session.add(other)
    session.flush()
    rows = []
    for index, (kind, status) in enumerate([
        ("lost", "available"), ("found", "claimed"),
        ("found", "available"), ("found", "returned"),
    ]):
        item = Item(
            id=UUID(int=index + 1), type=kind, status=status,
            name=f"{marker} Bottle {index}", description="Blue  strap",
            category="Electronics", date=date(2026, 10, 28), location="Library",
            created_by=owner if index != 1 else other.id,
            created_at=datetime(2020 if index == 0 else 2021, 1, 1, tzinfo=timezone.utc),
        )
        # Random identifiers avoid collisions with existing development records;
        # use adjacent UUIDs to make the tie-break ordering deterministic.
        rows.append(item)
    base = uuid4().int & ~3
    for index, item in enumerate(rows):
        item.id = UUID(int=base + index)
    session.add_all(rows)
    session.flush()
    return client, session, marker, rows


def test_active_listing_order_and_metadata(listings):
    client, _, marker, rows = listings
    response = client.get("/api/v1/items", params={"q": marker})
    assert response.status_code == 200
    body = response.json()
    assert (body["limit"], body["offset"], body["total"]) == (20, 0, 3)
    assert [item["id"] for item in body["data"]] == [str(rows[i].id) for i in (2, 1, 0)]
    assert {item["type"] for item in body["data"]} == {"lost", "found"}
    assert {item["status"] for item in body["data"]} == {"available", "claimed"}
    assert all(item["created_at"].endswith("Z") for item in body["data"])


def test_unfiltered_listing(api):
    client, _, _ = api
    response = client.get("/api/v1/items")
    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 20 and body["offset"] == 0
    assert body["total"] >= len(body["data"])
    assert all(item["status"] != "returned" for item in body["data"])


@pytest.mark.parametrize("field", ["name", "category", "description"])
def test_search_each_field_case_insensitive(listings, field):
    client, session, marker, rows = listings
    setattr(rows[0], field, f"Prefix Needle{marker} Suffix")
    session.flush()
    response = client.get("/api/v1/items", params={"q": f"  needle{marker.upper()}  "})
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["data"][0]["id"] == str(rows[0].id)


@pytest.mark.parametrize("literal", ["%", "_", "/", "\\", "' OR 1=1 --"])
def test_literal_search(listings, literal):
    client, session, marker, rows = listings
    rows[0].description = f"{marker}{literal}suffix"
    session.flush()
    body = client.get("/api/v1/items", params={"q": f"{marker}{literal}"}).json()
    assert body["total"] == 1
    assert body["data"][0]["id"] == str(rows[0].id)


def test_location_and_date_are_not_search_fields(listings):
    client, session, marker, rows = listings
    needle = str(uuid4())
    rows[0].location = needle
    session.flush()
    assert client.get("/api/v1/items", params={"q": needle}).json()["total"] == 0


def test_pagination_and_empty_results(listings):
    client, _, marker, rows = listings
    body = client.get("/api/v1/items", params={"q": marker, "limit": 1, "offset": 1}).json()
    assert (body["limit"], body["offset"], body["total"]) == (1, 1, 3)
    assert [item["id"] for item in body["data"]] == [str(rows[1].id)]
    body = client.get("/api/v1/items", params={"q": marker, "offset": 3}).json()
    assert body["data"] == [] and body["total"] == 3
    body = client.get("/api/v1/items", params={"q": str(uuid4()), "limit": 100}).json()
    assert body["data"] == [] and body["total"] == 0 and body["limit"] == 100


@pytest.mark.parametrize("offset", [3, 4, 2**63 - 1, 2**63, 10**100])
@pytest.mark.parametrize("has_matches", [True, False])
def test_out_of_range_offset_skips_page_query(listings, monkeypatch, offset, has_matches):
    client, session, marker, _ = listings

    def unexpected_page_query(*args, **kwargs):
        pytest.fail("Offsets beyond the matching total must not reach the page query")

    monkeypatch.setattr(session, "scalars", unexpected_page_query)
    response = client.get("/api/v1/items", params={
        "q": marker if has_matches else str(uuid4()), "limit": 7, "offset": str(offset),
    })
    assert response.status_code == 200, response.text
    assert response.json() == {
        "data": [], "total": 3 if has_matches else 0, "limit": 7, "offset": offset,
    }


@pytest.mark.parametrize("params", [
    {"limit": "0"}, {"limit": "101"}, {"limit": "abc"}, {"limit": "1.0"},
    {"offset": "-1"}, {"offset": "abc"}, {"offset": "1.5"},
    {"q": ""}, {"q": " \t "}, {"q": "x" * 201},
])
def test_invalid_parameters(api, params):
    client, _, _ = api
    response = client.get("/api/v1/items", params=params)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"][0]["field"].startswith("query.")


def test_database_failure(api, monkeypatch):
    client, session, _ = api

    def fail(*args, **kwargs):
        raise SQLAlchemyError("private database details")

    monkeypatch.setattr(session, "scalar", fail)
    response = client.get("/api/v1/items")
    assert response.status_code == 500
    assert response.json() == {"error": {
        "code": "INTERNAL_ERROR", "message": "Unable to list items.", "details": []
    }}
