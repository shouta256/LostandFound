"""Model checks using a disposable in-memory database, never PostgreSQL."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import UniqueConstraint, create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models import User


@pytest.fixture
def session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    User.__table__.create(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_user_structure():
    table = User.__table__
    assert table.name == "users"
    assert set(table.columns.keys()) == {
        "id", "google_sub", "email", "name", "role"
    }
    assert list(table.primary_key.columns.keys()) == ["id"]
    assert table.c.id.type.as_uuid
    assert {column.name for column in table.columns if column.nullable} == {"name"}
    assert any(
        isinstance(constraint, UniqueConstraint)
        and list(constraint.columns.keys()) == ["google_sub"]
        for constraint in table.constraints
    )


def test_defaults_and_team_role(session):
    student = User(google_sub="student-sub", email="student@example.com")
    team_member = User(
        google_sub="team-sub", email="team@example.com", name="Reviewer",
        role="team_member",
    )
    session.add_all([student, team_member])
    session.flush()
    assert isinstance(student.id, UUID)
    assert isinstance(team_member.id, UUID)
    assert student.id != team_member.id
    assert student.role == "student"
    assert student.name is None
    assert team_member.role == "team_member"
    assert team_member.name == "Reviewer"


def test_server_role_default(session):
    session.execute(
        text(
            "INSERT INTO users (id, google_sub, email) "
            "VALUES (:id, :google_sub, :email)"
        ),
        {"id": uuid4().hex, "google_sub": "server-default-sub",
         "email": "default@example.com"},
    )
    assert session.query(User).one().role == "student"


def test_duplicate_google_identity_rejected(session):
    session.add(User(google_sub="same-sub", email="first@example.com"))
    session.flush()
    session.add(User(google_sub="same-sub", email="second@example.com"))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_invalid_role_rejected(session):
    session.add(User(google_sub="invalid-sub", email="user@example.com", role="admin"))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()
