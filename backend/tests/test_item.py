"""Item checks in disposable SQLite; the development database is never used."""

from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, event, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models import Item, User


@pytest.fixture
def session():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    User.__table__.create(engine)
    Item.__table__.create(engine)
    with Session(engine) as session:
        session.add(User(google_sub="owner-sub", email="owner@example.com"))
        session.flush()
        yield session
    engine.dispose()


def item_values(session, **overrides):
    values = dict(
        type="found", name="Water Bottle", description="Blue  bottle",
        category="Personal items", date=date(2026, 10, 28), location="Library",
        created_by=session.scalars(select(User.id)).one(),
    )
    values.update(overrides)
    return values


def test_structure():
    table = Item.__table__
    assert set(table.columns.keys()) == {
        "id", "type", "name", "description", "category", "date", "location",
        "status", "created_by", "created_at", "updated_at",
    }
    assert list(table.primary_key.columns.keys()) == ["id"]
    assert all(not column.nullable for column in table.columns)
    assert table.c.id.type.as_uuid
    assert {fk.target_fullname for fk in table.c.created_by.foreign_keys} == {"users.id"}
    assert table.c.created_at.type.timezone
    assert table.c.updated_at.type.timezone


def test_defaults_relationship_and_persistence(session):
    item = Item(**item_values(session, name=" \tWater Bottle\n "))
    session.add(item)
    session.flush()
    assert isinstance(item.id, UUID)
    assert item.status == "available"
    assert item.name == "Water Bottle"
    assert item.description == "Blue  bottle"
    assert item.creator.id == item.created_by
    assert item.created_at.utcoffset() == timedelta(0)
    assert item.updated_at.utcoffset() == timedelta(0)
    identifier = item.id
    session.expire_all()
    loaded = session.get(Item, identifier)
    assert loaded.date == date(2026, 10, 28)
    assert loaded.creator.email == "owner@example.com"


@pytest.mark.parametrize("field,limit", [
    ("name", 120), ("description", 2000), ("category", 80), ("location", 200),
])
def test_text_validation(session, field, limit):
    assert getattr(Item(**item_values(session, **{field: " " + "x" * limit + " "})), field) == "x" * limit
    for invalid in (" \t\n", "x" * (limit + 1)):
        with pytest.raises(ValueError):
            Item(**item_values(session, **{field: invalid}))


@pytest.mark.parametrize("overrides", [
    {"type": "other"}, {"status": "other"}, {"type": "lost", "status": "claimed"},
    {"created_by": uuid4()}, {"date": None}, {"created_by": None},
    {"name": ""}, {"description": " "}, {"category": "x" * 81},
    {"name": "x" * 121}, {"description": "x" * 2001}, {"location": "x" * 201},
])
def test_database_constraints(session, overrides):
    # Core inserts bypass ORM text validation, exercising database safeguards.
    with pytest.raises(IntegrityError):
        session.execute(insert(Item.__table__).values(**item_values(session, **overrides)))
        session.flush()
    session.rollback()


@pytest.mark.parametrize("item_type,status", [
    ("lost", "available"), ("lost", "returned"), ("found", "available"),
    ("found", "claimed"), ("found", "returned"),
])
def test_allowed_states(session, item_type, status):
    session.add(Item(**item_values(session, type=item_type, status=status)))
    session.flush()


def test_server_defaults(session):
    identifier = uuid4()
    session.connection().exec_driver_sql(
        "INSERT INTO items (id, type, name, description, category, date, location, created_by) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (identifier.hex, "found", "Bottle", "Blue", "Other", "2026-10-28",
         "Library", item_values(session)["created_by"].hex),
    )
    item = session.get(Item, identifier)
    assert item.status == "available"
    assert item.created_at is not None
    assert item.updated_at is not None


def test_update_and_repeated_status_timestamps(session):
    original = datetime(2020, 1, 1, tzinfo=timezone.utc)
    item = Item(**item_values(session), created_at=original, updated_at=original)
    session.add(item)
    session.flush()
    item.status = "claimed"
    session.flush()
    changed = item.updated_at
    assert changed > original
    assert item.created_at == original
    item.status = "claimed"
    session.flush()
    assert item.updated_at == changed
