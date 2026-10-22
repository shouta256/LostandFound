from uuid import UUID

from sqlalchemy import func, select

from app.models import Item
from app.seed import seed_items


def test_seed_is_repeatable_and_preserves_existing_changes(db):
    assert seed_items(db) == 5
    db.commit()
    item = db.get(Item, UUID("00000000-0000-4000-8000-000000000001"))
    item.name = "Edited by a teammate"
    db.commit()
    assert seed_items(db) == 0
    db.commit()
    assert db.scalar(select(func.count()).select_from(Item)) == 5
    db.refresh(item)
    assert item.name == "Edited by a teammate"
