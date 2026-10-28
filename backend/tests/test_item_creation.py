"""Exercise only item creation; PostgreSQL tests roll back an outer transaction."""

import os
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.database import engine as postgres_engine, get_db
from backend.app.items import create_items_router
from backend.app.models import Item, User


PAYLOAD = dict(name="Bottle", description="Blue  bottle", category="Other",
               type="found", date="2026-10-28", location="Library")


@pytest.fixture(params=["sqlite", "postgresql"])
def api(request):
    postgres = request.param == "postgresql"
    if postgres and os.environ.get("RUN_POSTGRES_TESTS") != "1":
        pytest.skip("Set RUN_POSTGRES_TESTS=1 to test the migrated local PostgreSQL database")
    engine = postgres_engine if postgres else create_engine(
        "sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    if not postgres:
        @event.listens_for(engine, "connect")
        def sqlite_connect(connection, record):
            connection.isolation_level = None
            connection.execute("PRAGMA foreign_keys=ON")

        @event.listens_for(engine, "begin")
        def sqlite_begin(connection):
            connection.exec_driver_sql("BEGIN")
    with engine.connect() as connection:
        if postgres:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "bd0aa1e087a6"
            connection.rollback()
        else:
            User.__table__.create(connection)
            Item.__table__.create(connection)
            connection.commit()
        outer = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        identifier = uuid4()
        user = User(id=identifier, google_sub=f"test-{identifier}", email="test@example.com")
        session.add(user)
        session.flush()

        def current_user():
            return user

        def database():
            yield session

        app = FastAPI()
        app.include_router(create_items_router(current_user))
        app.dependency_overrides[get_db] = database
        try:
            # Sync endpoints run in workers; SQLite permits sequential cross-thread use.
            with TestClient(app) as client:
                yield client, session, identifier
        finally:
            session.close()
            outer.rollback()
        assert connection.get_transaction() is None
        assert connection.get_nested_transaction() is None
        if postgres:
            assert connection.scalar(select(User.id).where(User.id == identifier)) is None
            assert connection.scalar(select(Item.id).where(Item.created_by == identifier)) is None
    if not postgres:
        engine.dispose()


@pytest.mark.parametrize("item_type", ["lost", "found"])
def test_create_item(api, item_type):
    client, session, owner = api
    response = client.post("/api/v1/items", json={
        **PAYLOAD, "name": " \tBottle\n ", "type": item_type,
    })
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Bottle"
    assert body["description"] == "Blue  bottle"
    assert body["status"] == "available"
    assert body["type"] == item_type
    assert body["created_by"] == str(owner)
    assert body["created_at"].endswith("Z") and body["updated_at"].endswith("Z")
    assert response.headers["location"] == f"/api/v1/items/{body['id']}"
    assert session.get(Item, UUID(body["id"])).created_by == owner


@pytest.mark.parametrize("changes", [
    {"name": " \t "}, {"name": "x" * 121}, {"description": "x" * 2001},
    {"category": "x" * 81}, {"location": "x" * 201}, {"type": "other"},
    {"date": "2026-02-30"}, {"date": "20261028"}, {"date": 0},
    {"created_by": str(uuid4())}, {"status": "returned"}, {"name": None},
])
def test_invalid_input(api, changes):
    client, session, owner = api
    response = client.post("/api/v1/items", json={**PAYLOAD, **changes})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["details"]


@pytest.mark.parametrize("field", PAYLOAD.keys())
def test_required_fields(api, field):
    client, _, _ = api
    payload = PAYLOAD.copy()
    del payload[field]
    assert client.post("/api/v1/items", json=payload).status_code == 422


def test_json_and_media_errors(api):
    client, _, _ = api
    response = client.post("/api/v1/items", content="{", headers={"Content-Type": "application/json"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_JSON"
    response = client.post("/api/v1/items", content="text", headers={"Content-Type": "text/plain"})
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_database_error(api, monkeypatch):
    client, session, _ = api

    def fail():
        raise SQLAlchemyError("private database connection details")

    monkeypatch.setattr(session, "flush", fail)
    response = client.post("/api/v1/items", json=PAYLOAD)
    assert response.status_code == 500
    assert response.json() == {"error": {
        "code": "INTERNAL_ERROR", "message": "Unable to create item.", "details": []
    }}
