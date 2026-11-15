from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from pydantic import StringConstraints
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.auth import require_json
from app.auth import get_current_user, require_team_member
from app.database import get_db
from app.errors import APIError
from app.models import Claim, Item, ItemPhoto, User
from app.schemas import ItemCreate, ItemPage, ItemResponse, ItemStatusUpdate

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


@router.patch("/items/{item_id}/status", response_model=ItemResponse, operation_id="updateItemStatus",
              dependencies=[Depends(require_json)])
def update_item_status(
    item_id: UUID,
    body: ItemStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
    _team_member: Annotated[User, Depends(require_team_member)],
) -> ItemResponse:
    item = db.scalar(select(Item).where(Item.id == item_id).with_for_update())
    if item is None:
        raise APIError(404, "ITEM_NOT_FOUND", "Item not found.")
    if body.status == item.status:
        return ItemResponse.model_validate(item)
    allowed = {"found": {"available": "claimed", "claimed": "returned"},
               "lost": {"available": "returned"}}
    if allowed[item.type].get(item.status) != body.status:
        raise APIError(409, "INVALID_STATUS_TRANSITION", "The item status transition is not allowed.")
    if body.status == "claimed" and db.scalar(select(Claim.id).where(
        Claim.item_id == item.id, Claim.status == "approved"
    )) is None:
        raise APIError(409, "INVALID_STATUS_TRANSITION", "An approved claim is required to mark an item claimed.")
    item.status = body.status
    item.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return ItemResponse.model_validate(item)


MAX_PHOTO_SIZE = 5 * 1024 * 1024
PHOTO_SIGNATURES = {"image/jpeg": b"\xff\xd8\xff", "image/png": b"\x89PNG\r\n\x1a\n", "image/webp": b"RIFF"}


@router.put("/items/{item_id}/photo", response_model=ItemResponse, operation_id="uploadItemPhoto")
async def upload_item_photo(
    item_id: UUID,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ItemResponse:
    item = db.scalar(select(Item).where(Item.id == item_id).with_for_update())
    if item is None:
        raise APIError(404, "ITEM_NOT_FOUND", "Item not found.")
    if item.created_by != current_user.id:
        raise APIError(403, "FORBIDDEN", "Only the item's creator can upload a photo.")
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type not in PHOTO_SIGNATURES:
        raise APIError(415, "UNSUPPORTED_MEDIA_TYPE", "Use a JPEG, PNG or WebP photo.")
    content_length = request.headers.get("content-length", "")
    if content_length.isdecimal() and int(content_length) > MAX_PHOTO_SIZE:
        raise APIError(413, "PAYLOAD_TOO_LARGE", "Photos must be at most 5 MiB.")
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > MAX_PHOTO_SIZE:
            raise APIError(413, "PAYLOAD_TOO_LARGE", "Photos must be at most 5 MiB.")
        data.extend(chunk)
    if not data.startswith(PHOTO_SIGNATURES[content_type]) or (
        content_type == "image/webp" and data[8:12] != b"WEBP"
    ):
        raise RequestValidationError([{"type": "value_error", "loc": ("body",),
                                       "msg": "Invalid value.", "input": None}])
    now = datetime.now(timezone.utc)
    photo = db.get(ItemPhoto, item.id)
    if photo is None:
        photo = ItemPhoto(item_id=item.id)
        db.add(photo)
    photo.content_type = content_type
    photo.data = bytes(data)
    photo.updated_at = now
    item.photo_updated_at = now
    item.updated_at = now
    db.commit()
    db.refresh(item)
    response.headers["Cache-Control"] = "no-store"
    return ItemResponse.model_validate(item)


@router.get("/items/{item_id}/photo", operation_id="getItemPhoto")
def get_item_photo(
    item_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    if db.get(Item, item_id) is None:
        raise APIError(404, "ITEM_NOT_FOUND", "Item not found.")
    photo = db.get(ItemPhoto, item_id)
    if photo is None:
        raise APIError(404, "PHOTO_NOT_FOUND", "Photo not found.")
    return Response(content=photo.data, media_type=photo.content_type, headers={
        "Cache-Control": "public, max-age=31536000, immutable",
        "X-Content-Type-Options": "nosniff",
    })
