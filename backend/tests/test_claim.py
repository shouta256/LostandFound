"""Claim constraints exercised in disposable SQLite, never the development DB."""

from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, event, insert, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateIndex

from backend.app.models import Claim, Item, User


@pytest.fixture
def session():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    for model in (User, Item, Claim):
        model.__table__.create(engine)
    with Session(engine) as session:
        users = [User(google_sub=str(i), email=f"user{i}@example.com") for i in range(4)]
        session.add_all(users)
        session.flush()
        for name in ("Bottle", "Keys"):
            session.add(Item(
                type="found", name=name, description="Found on campus", category="Other",
                date=date(2026, 10, 28), location="Library", creator=users[0],
            ))
        session.flush()
        yield session
    engine.dispose()


def values(session, **overrides):
    users = session.scalars(select(User).order_by(User.google_sub)).all()
    item = session.scalars(select(Item).order_by(Item.name)).first()
    result = dict(item_id=item.id, claimant_id=users[1].id, ownership_information="Blue  strap")
    result.update(overrides)
    return result


def review(session):
    reviewer = session.scalars(select(User).where(User.google_sub == "3")).one()
    return dict(reviewed_by=reviewer.id, reviewed_at=datetime.now(timezone.utc))


def test_structure_and_postgresql_indexes():
    table = Claim.__table__
    assert set(table.c.keys()) == {
        "id", "item_id", "claimant_id", "ownership_information", "status",
        "reviewed_by", "reviewed_at", "created_at", "updated_at",
    }
    assert list(table.primary_key.columns.keys()) == ["id"]
    assert {c.name for c in table.c if c.nullable} == {"reviewed_by", "reviewed_at"}
    assert table.c.id.type.as_uuid
    for column in ("created_at", "updated_at", "reviewed_at"):
        assert table.c[column].type.timezone
    ddl = {i.name: str(CreateIndex(i).compile(dialect=postgresql.dialect())) for i in table.indexes}
    assert "UNIQUE INDEX" in ddl["uq_claims_pending_user_item"]
    assert "(item_id, claimant_id) WHERE status = 'pending'" in ddl["uq_claims_pending_user_item"]
    assert "(item_id) WHERE status = 'approved'" in ddl["uq_claims_approved_item"]


def test_defaults_relationships_and_persistence(session):
    claim = Claim(**values(session, ownership_information=" \tBlue  strap\n"))
    session.add(claim)
    session.flush()
    assert isinstance(claim.id, UUID)
    assert claim.status == "pending"
    assert claim.reviewed_by is None and claim.reviewed_at is None
    assert claim.reviewer is None
    assert claim.created_at.utcoffset() == timedelta(0)
    assert claim.updated_at.utcoffset() == timedelta(0)
    identifier = claim.id
    session.expire_all()
    loaded = session.get(Claim, identifier)
    assert loaded.ownership_information == "Blue  strap"
    assert loaded.claimant.id == loaded.claimant_id
    assert loaded.item.id == loaded.item_id
    assert loaded.item.status == "available"


def test_duplicate_pending_rejected(session):
    session.add(Claim(**values(session)))
    session.flush()
    with pytest.raises(IntegrityError):
        session.execute(insert(Claim.__table__).values(**values(session)))
    session.rollback()


def test_multiple_claimants_and_items_allowed(session):
    initial = values(session)
    other_user = session.scalars(select(User).where(User.google_sub == "2")).one()
    other_item = session.scalars(select(Item).where(Item.id != initial["item_id"])).one()
    session.add_all([
        Claim(**initial), Claim(**values(session, claimant_id=other_user.id)),
        Claim(**values(session, item_id=other_item.id)),
    ])
    session.flush()


def test_reapplication_after_rejection(session):
    rejected = Claim(**values(session, status="rejected", **review(session)))
    session.add(rejected)
    session.flush()
    session.add(Claim(**values(session)))
    session.flush()
    assert rejected.reviewer.id == rejected.reviewed_by
    assert rejected.item.status == "available"


def test_only_one_approval_preserves_other_pending_claims(session):
    first = Claim(**values(session, status="approved", **review(session)))
    other_user = session.scalars(select(User).where(User.google_sub == "2")).one()
    second = Claim(**values(session, claimant_id=other_user.id))
    session.add_all([first, second])
    session.flush()
    assert second.status == "pending"
    second.status = "approved"
    second.reviewed_by = first.reviewed_by
    second.reviewed_at = first.reviewed_at
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


@pytest.mark.parametrize("overrides", [
    {"status": "other"}, {"ownership_information": ""},
    {"ownership_information": " "}, {"ownership_information": "x" * 2001},
    {"ownership_information": None}, {"item_id": uuid4()}, {"claimant_id": uuid4()},
    {"status": "approved"}, {"status": "rejected"}, {"item_id": None},
    {"claimant_id": None}, {"reviewed_at": datetime.now(timezone.utc)},
])
def test_database_constraints(session, overrides):
    with pytest.raises(IntegrityError):
        session.execute(insert(Claim.__table__).values(**values(session, **overrides)))
    session.rollback()


def test_self_review_rejected(session):
    data = values(session)
    with pytest.raises(IntegrityError):
        session.execute(insert(Claim.__table__).values(
            **data, status="approved", reviewed_by=data["claimant_id"],
            reviewed_at=datetime.now(timezone.utc),
        ))
    session.rollback()


def test_text_validation(session):
    assert len(Claim(**values(session, ownership_information=" " + "x" * 2000 + " ")).ownership_information) == 2000
    for value in (" \t\n", "x" * 2001):
        with pytest.raises(ValueError):
            Claim(**values(session, ownership_information=value))


def test_server_defaults(session):
    data = values(session)
    identifier = uuid4()
    session.connection().exec_driver_sql(
        "INSERT INTO claims (id, item_id, claimant_id, ownership_information) VALUES (?, ?, ?, ?)",
        (identifier.hex, data["item_id"].hex, data["claimant_id"].hex, "Evidence"),
    )
    claim = session.get(Claim, identifier)
    assert claim.status == "pending"
    assert claim.reviewed_at is None and claim.reviewed_by is None
    assert claim.created_at is not None and claim.updated_at is not None


def test_update_and_repeated_decision_timestamps(session):
    original = datetime(2020, 1, 1, tzinfo=timezone.utc)
    claim = Claim(**values(session), created_at=original, updated_at=original)
    session.add(claim)
    session.flush()
    decision = review(session)
    claim.status = "rejected"
    claim.reviewed_by = decision["reviewed_by"]
    claim.reviewed_at = decision["reviewed_at"]
    session.flush()
    changed = claim.updated_at
    assert changed > original
    claim.status = "rejected"
    session.flush()
    assert claim.updated_at == changed
    assert claim.created_at == original
    assert claim.reviewed_at == decision["reviewed_at"]
