"""Pickup model tests use only disposable in-memory SQLite."""

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models import Claim, Item, Pickup, User


@pytest.fixture
def session():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    for model in (User, Item, Claim, Pickup):
        model.__table__.create(engine)
    with Session(engine) as session:
        owner = User(google_sub="owner", email="owner@example.com")
        claimant = User(google_sub="claimant", email="claimant@example.com")
        reviewer = User(google_sub="reviewer", email="reviewer@example.com", role="team_member")
        item = Item(
            type="found", name="Bottle", description="Blue bottle", category="Other",
            date=date(2026, 10, 28), location="Library", creator=owner, status="claimed",
        )
        session.add(Claim(
            item=item, claimant=claimant, ownership_information="Blue strap",
            status="approved", reviewer=reviewer, reviewed_at=datetime.now(timezone.utc),
        ))
        session.flush()
        yield session
    engine.dispose()


def claim_id(session):
    return session.scalars(select(Claim.id)).one()


def test_structure():
    table = Pickup.__table__
    assert set(table.c.keys()) == {"claim_id", "location", "status", "ready_at"}
    assert list(table.primary_key.columns.keys()) == ["claim_id"]
    assert table.c.claim_id.type.as_uuid
    assert {fk.target_fullname for fk in table.c.claim_id.foreign_keys} == {"claims.id"}
    assert {c.name for c in table.c if c.nullable} == {"ready_at"}
    assert table.c.ready_at.type.timezone


def test_defaults_relationship_and_persistence(session):
    claim = session.scalars(select(Claim)).one()
    assert claim.pickup is None
    pickup = Pickup(claim=claim, location=" \tCampus  Office\n")
    session.add(pickup)
    session.flush()
    assert pickup.status == "not_ready"
    assert pickup.ready_at is None
    assert claim.pickup is pickup
    assert pickup.claim_id == claim.id
    identifier = claim.id
    session.expire_all()
    loaded = session.get(Pickup, identifier)
    assert loaded.location == "Campus  Office"
    assert loaded.claim.pickup is loaded


def test_ready_record(session):
    ready_at = datetime.now(timezone.utc)
    pickup = Pickup(claim_id=claim_id(session), location="Office", status="ready", ready_at=ready_at)
    session.add(pickup)
    session.flush()
    assert pickup.ready_at == ready_at
    assert pickup.ready_at.utcoffset().total_seconds() == 0
    # A location edit must not replace the recorded readiness time.
    pickup.location = "Other office"
    session.flush()
    assert pickup.ready_at == ready_at


def test_duplicate_pickup_rejected(session):
    data = dict(claim_id=claim_id(session), location="Office")
    session.execute(insert(Pickup.__table__).values(**data))
    with pytest.raises(IntegrityError):
        session.execute(insert(Pickup.__table__).values(**data))
    session.rollback()


@pytest.mark.parametrize("overrides", [
    {"claim_id": uuid4()}, {"location": None}, {"location": ""},
    {"location": "   "}, {"location": "x" * 201}, {"status": "other"},
    {"status": None}, {"status": "ready", "ready_at": None},
    {"status": "not_ready", "ready_at": datetime.now(timezone.utc)},
])
def test_invalid_database_values(session, overrides):
    data = dict(claim_id=claim_id(session), location="Office")
    data.update(overrides)
    with pytest.raises(IntegrityError):
        session.execute(insert(Pickup.__table__).values(**data))
    session.rollback()


def test_location_validation(session):
    pickup = Pickup(claim_id=claim_id(session), location=" " + "x" * 200 + " ")
    assert pickup.location == "x" * 200
    session.add(pickup)
    session.flush()
    for invalid in (" \t\n", "x" * 201):
        with pytest.raises(ValueError):
            Pickup(location=invalid)


def test_server_default(session):
    identifier = claim_id(session)
    session.connection().exec_driver_sql(
        "INSERT INTO pickups (claim_id, location) VALUES (?, ?)",
        (identifier.hex, "Office"),
    )
    pickup = session.get(Pickup, identifier)
    assert pickup.status == "not_ready"
    assert pickup.ready_at is None
