"""Check worker execution, per-request sessions and concurrent responsiveness."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock, get_ident
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from backend.app import database
from backend.app.items import create_items_router
from backend.app.models import User
from backend.tests.test_item_creation import PAYLOAD, api  # noqa: F401


def assert_worker():
    with pytest.raises(RuntimeError, match="no running event loop"):
        asyncio.get_running_loop()


def test_all_item_database_operations_run_outside_event_loop(api, monkeypatch):
    client, session, owner = api
    session.get(User, owner).role = "team_member"
    session.flush()
    observed = []
    for name in ("get", "scalar", "scalars", "add", "flush", "commit", "rollback"):
        original = getattr(session, name)

        def checked(*args, _original=original, _name=name, **kwargs):
            assert_worker()
            observed.append(_name)
            return _original(*args, **kwargs)

        monkeypatch.setattr(session, name, checked)
    response = client.post("/api/v1/items", json={**PAYLOAD, "type": "lost"})
    assert response.status_code == 201
    identifier = response.json()["id"]
    assert client.get(f"/api/v1/items/{identifier}").status_code == 200
    assert client.get("/api/v1/items").status_code == 200
    assert client.patch(f"/api/v1/items/{identifier}/status", json={"status": "returned"}).status_code == 200
    assert {"get", "scalar", "scalars", "add", "flush", "commit"} <= set(observed)


@pytest.mark.parametrize("fail", [False, True])
def test_concurrent_requests_have_separate_sessions_and_cleanup(monkeypatch, fail):
    started = Event()
    release = Event()
    lock = Lock()
    sessions = []

    class TrackedSession:
        def __init__(self):
            assert_worker()
            self.closed = False
            self.rollbacks = 0
            self.authenticated = False
            self.query_thread = None
            with lock:
                self.number = len(sessions)
                sessions.append(self)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            assert_worker()
            self.closed = True

        def scalar(self, statement):
            assert_worker()
            assert self.authenticated and not self.closed
            self.query_thread = get_ident()
            if self.number == 0:
                started.set()
                assert release.wait(5), "Concurrent request could not run while database call waited"
                if fail:
                    raise SQLAlchemyError("simulated database failure")
            return 0

        def rollback(self):
            assert_worker()
            self.rollbacks += 1

    monkeypatch.setattr(database, "SessionLocal", TrackedSession)

    def current_user(session=Depends(database.get_db)):
        assert_worker()
        assert not session.authenticated
        session.authenticated = True
        return User(id=uuid4(), role="student")

    app = FastAPI()
    app.include_router(create_items_router(current_user))
    with TestClient(app) as client, ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(client.get, "/api/v1/items")
        try:
            assert started.wait(5)
            # This must finish before the blocked query is released. Both calls
            # use the same ASGI event loop but separate dependency-owned sessions.
            second = executor.submit(client.get, "/api/v1/items")
            assert second.result(timeout=3).status_code == 200
        finally:
            release.set()
        assert first.result(timeout=5).status_code == (500 if fail else 200)
    assert len(sessions) == 2
    assert all(session.closed for session in sessions)
    assert all(session.authenticated for session in sessions)
    assert sessions[0].query_thread != sessions[1].query_thread
    assert sessions[0].rollbacks == int(fail)
    assert sessions[1].rollbacks == 0
