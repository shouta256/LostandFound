"""Item creation, listing and details with an injected current-user dependency."""

import re
from collections.abc import Callable
from datetime import date, datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .database import get_db
from .models import Claim, Item, User


class ItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=2000)
    category: str = Field(min_length=1, max_length=80)
    type: Literal["lost", "found"]
    date: date
    location: str = Field(min_length=1, max_length=200)

    @field_validator("date", mode="before")
    @classmethod
    def validate_date(cls, value):
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("Date must use YYYY-MM-DD")
        return value


class ItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: Literal["lost", "found"]
    name: str
    description: str
    category: str
    date: date
    location: str
    status: Literal["available", "claimed", "returned"]
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def normalize_utc(cls, value):
        # SQLite test storage loses timezone information; PostgreSQL preserves it.
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


def error_response(status, code, message, details=None):
    return JSONResponse(status_code=status, content={
        "error": {"code": code, "message": message, "details": details or []}
    })


async def read_item_json(request: Request):
    """Read the ASGI body asynchronously without doing any database work."""
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
        return error_response(415, "UNSUPPORTED_MEDIA_TYPE", "Use application/json.")
    try:
        return await request.json()
    except (ValueError, UnicodeDecodeError):
        return error_response(400, "INVALID_JSON", "Malformed JSON.")


class ItemQuery(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    q: str | None = Field(default=None, min_length=1, max_length=200)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

    @field_validator("limit", "offset", mode="before")
    @classmethod
    def validate_integer(cls, value):
        if isinstance(value, str) and not re.fullmatch(r"[+-]?[0-9]+", value):
            raise ValueError("Must be an integer")
        return value


class ItemPage(BaseModel):
    data: list[ItemResponse]
    limit: int
    offset: int
    total: int


class ItemStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["available", "claimed", "returned"]


def create_items_router(current_user: Callable) -> APIRouter:
    """Mount directly in the host app; current_user must return a stored User.

    Authentication failures and their contract responses belong to that shared
    dependency. Development tests override it with a disposable database user.
    """
    router = APIRouter(prefix="/api/v1", tags=["Items"])

    @router.patch("/items/{item_id}/status", response_model=ItemResponse, operation_id="updateItemStatus")
    def update_item_status(
        item_id: str,
        request: Request,
        user: Annotated[User, Depends(current_user)],
        session: Annotated[Session, Depends(get_db)],
        payload: Annotated[object, Depends(read_item_json)],
    ):
        if user.role != "team_member":
            return error_response(403, "FORBIDDEN", "Team members only.")
        try:
            identifier = UUID(item_id)
        except ValueError:
            return error_response(422, "VALIDATION_ERROR", "Invalid item identifier.", [
                {"field": "path.item_id", "message": "Must be a valid UUID"}
            ])
        if isinstance(payload, JSONResponse):
            return payload
        try:
            data = ItemStatusUpdate.model_validate(payload)
        except ValidationError as exc:
            details = [
                {"field": ".".join(["body", *map(str, entry["loc"])]), "message": entry["msg"]}
                for entry in exc.errors(include_input=False, include_context=False)
            ]
            return error_response(422, "VALIDATION_ERROR", "Invalid status data.", details)
        try:
            # Serialize status writers and reload any previously cached item state.
            item = session.scalar(
                select(Item).where(Item.id == identifier).with_for_update()
                .execution_options(populate_existing=True)
            )
            if item is None:
                return error_response(404, "ITEM_NOT_FOUND", "Item not found.")
            if data.status != item.status:
                allowed = (
                    {("available", "claimed"), ("claimed", "returned")}
                    if item.type == "found" else {("available", "returned")}
                )
                valid = (item.status, data.status) in allowed
                if valid and data.status == "claimed":
                    valid = session.scalar(select(Claim.id).where(
                        Claim.item_id == item.id, Claim.status == "approved"
                    )) is not None
                if not valid:
                    return error_response(409, "INVALID_STATUS_TRANSITION", "Invalid status transition.")
                item.status = data.status
                session.flush()
            # Repeated statuses perform no update, preserving all timestamps.
            result = ItemResponse.model_validate(item).model_dump(mode="json")
            session.commit()
            return JSONResponse(content=result)
        except SQLAlchemyError:
            session.rollback()
            return error_response(500, "INTERNAL_ERROR", "Unable to update item status.")

    @router.get("/items/{item_id}", response_model=ItemResponse, operation_id="getItem")
    def get_item(
        item_id: str,
        user: Annotated[User, Depends(current_user)],
        session: Annotated[Session, Depends(get_db)],
    ):
        try:
            identifier = UUID(item_id)
        except ValueError:
            return error_response(
                422, "VALIDATION_ERROR", "Invalid item identifier.",
                [{"field": "path.item_id", "message": "Must be a valid UUID"}],
            )
        try:
            # All authenticated users can read listings, including returned items.
            item = session.get(Item, identifier)
            if item is None:
                return error_response(404, "ITEM_NOT_FOUND", "Item not found.")
            return ItemResponse.model_validate(item)
        except SQLAlchemyError:
            session.rollback()
            return error_response(500, "INTERNAL_ERROR", "Unable to retrieve item.")

    @router.get("/items", response_model=ItemPage, operation_id="listItems")
    def list_items(
        request: Request,
        user: Annotated[User, Depends(current_user)],
        session: Annotated[Session, Depends(get_db)],
    ):
        try:
            query = ItemQuery.model_validate(dict(request.query_params))
        except ValidationError as exc:
            details = [
                {"field": ".".join(["query", *map(str, entry["loc"])]),
                 "message": entry["msg"]}
                for entry in exc.errors(include_input=False, include_context=False)
            ]
            return error_response(422, "VALIDATION_ERROR", "Invalid listing parameters.", details)
        filters = [Item.status != "returned"]
        if query.q is not None:
            # Escape LIKE metacharacters so q remains a literal substring.
            literal = query.q.replace("/", "//").replace("%", "/%").replace("_", "/_")
            filters.append(or_(
                Item.name.ilike(f"%{literal}%", escape="/"),
                Item.category.ilike(f"%{literal}%", escape="/"),
                Item.description.ilike(f"%{literal}%", escape="/"),
            ))
        try:
            total = session.scalar(select(func.count()).select_from(Item).where(*filters))
            # Avoid sending offsets beyond the matching rows (or database integer
            # range) to PostgreSQL, while preserving the requested page metadata.
            if query.offset >= total:
                return ItemPage(data=[], limit=query.limit, offset=query.offset, total=total)
            items = session.scalars(
                select(Item).where(*filters)
                .order_by(Item.created_at.desc(), Item.id.desc())
                .limit(query.limit).offset(query.offset)
            ).all()
            return ItemPage(
                data=[ItemResponse.model_validate(item) for item in items],
                limit=query.limit, offset=query.offset, total=total,
            )
        except SQLAlchemyError:
            session.rollback()
            return error_response(500, "INTERNAL_ERROR", "Unable to list items.")

    @router.post("/items", status_code=201, response_model=ItemResponse, operation_id="createItem")
    def create_item(
        request: Request,
        user: Annotated[User, Depends(current_user)],
        session: Annotated[Session, Depends(get_db)],
        payload: Annotated[object, Depends(read_item_json)],
    ):
        if isinstance(payload, JSONResponse):
            return payload
        try:
            data = ItemCreate.model_validate(payload)
        except ValidationError as exc:
            details = [
                {"field": ".".join(["body", *map(str, entry["loc"])]),
                 "message": entry["msg"]}
                for entry in exc.errors(include_input=False, include_context=False)
            ]
            return error_response(422, "VALIDATION_ERROR", "Invalid item data.", details)
        try:
            item = Item(**data.model_dump(), created_by=user.id)
            session.add(item)
            session.flush()
            result = ItemResponse.model_validate(item).model_dump(mode="json")
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            return error_response(500, "INTERNAL_ERROR", "Unable to create item.")
        return JSONResponse(
            status_code=201, content=result,
            headers={"Location": f"/api/v1/items/{result['id']}"},
        )

    return router
