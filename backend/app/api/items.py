from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, Response
from pydantic import StringConstraints
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.auth import require_json
from app.auth import get_current_user
from app.database import get_db
from app.errors import APIError
from app.models import Item, User
from app.schemas import ItemCreate, ItemPage, ItemResponse

router = APIRouter()
SearchQuery = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
CategoryQuery = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


@router.post(
    "/items",
    response_model=ItemResponse,
    status_code=201,
    operation_id="createItem",
    dependencies=[Depends(require_json)],
)
def create_item(
    body: ItemCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    response: Response,
) -> ItemResponse:
    now = datetime.now(timezone.utc)
    item = Item(
        id=uuid4(),
        type=body.type,
        name=body.name,
        description=body.description,
        category=body.category,
        date=body.date,
        location=body.location,
        status="available",
        created_by=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    response.headers["Location"] = f"/api/v1/items/{item.id}"
    return ItemResponse.model_validate(item)


@router.get("/items", response_model=ItemPage, operation_id="listItems")
def read_items(
    db: Annotated[Session, Depends(get_db)],
    q: Annotated[SearchQuery | None, Query()] = None,
    type: Annotated[Literal["lost", "found"] | None, Query()] = None,
    category: Annotated[CategoryQuery | None, Query()] = None,
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
    if type is not None:
        conditions.append(Item.type == type)
    if category is not None:
        conditions.append(func.lower(Item.category) == category.lower())
    total = db.scalar(select(func.count()).select_from(Item).where(*conditions))
    items = db.scalars(
        select(Item).where(*conditions)
        .order_by(Item.created_at.desc(), Item.id.desc())
        .limit(limit).offset(offset)
    ).all()
    return ItemPage(data=items, total=total, limit=limit, offset=offset)


@router.get("/items/{item_id}", response_model=ItemResponse, operation_id="getItem")
def read_item(
    item_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> ItemResponse:
    item = db.get(Item, item_id)
    if item is None:
        raise APIError(404, "ITEM_NOT_FOUND", "Item not found.")
    return ItemResponse.model_validate(item)
