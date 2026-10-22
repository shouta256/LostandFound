from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.seed import seed_items


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
