from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import StringConstraints
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Item
from app.schemas import ItemPage

router = APIRouter()
SearchQuery = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


@router.get("/items", response_model=ItemPage, operation_id="listItems")
def read_items(
    db: Annotated[Session, Depends(get_db)],
    q: Annotated[SearchQuery | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ItemPage:
    conditions = [Item.status != "returned"]
    if q is not None:
        conditions.append(or_(
            Item.name.icontains(q, autoescape=True),
            Item.category.icontains(q, autoescape=True),
            Item.description.icontains(q, autoescape=True),
        ))
    total = db.scalar(select(func.count()).select_from(Item).where(*conditions))
    items = db.scalars(
        select(Item).where(*conditions)
        .order_by(Item.created_at.desc(), Item.id.desc())
        .limit(limit).offset(offset)
    ).all()
    return ItemPage(data=items, total=total, limit=limit, offset=offset)
