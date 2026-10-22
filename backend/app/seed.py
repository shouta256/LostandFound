"""Insert local sample items without duplicating or overwriting existing rows."""

from datetime import date, datetime, timezone
import json
from pathlib import Path
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Item


def seed_items(session: Session) -> int:
    samples = json.loads(Path(__file__).with_name("sample_items.json").read_text())
    rows = []
    for sample in samples:
        item_date = date.fromisoformat(sample["date"])
        timestamp = datetime.combine(item_date, datetime.min.time(), tzinfo=timezone.utc)
        rows.append({
            **sample,
            "id": UUID(sample["id"]),
            "date": item_date,
            "status": "available",
            "created_by": UUID("00000000-0000-4000-8000-000000000100"),
            "created_at": timestamp,
            "updated_at": timestamp,
        })
    result = session.scalars(
        insert(Item).values(rows).on_conflict_do_nothing(index_elements=[Item.id]).returning(Item.id)
    )
    return len(result.all())


if __name__ == "__main__":
    with SessionLocal.begin() as session:
        inserted = seed_items(session)
    print(f"Sample items: {inserted} inserted; existing items left unchanged.")
