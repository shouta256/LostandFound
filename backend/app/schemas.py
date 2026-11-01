import re
from datetime import date, datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


ItemName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
ItemDescription = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
ItemCategory = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
ItemLocation = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_token: str = Field(min_length=1, max_length=16384)


class ItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["lost", "found"]
    name: ItemName
    description: ItemDescription
    category: ItemCategory
    date: date
    location: ItemLocation

    @field_validator("date", mode="before")
    @classmethod
    def date_uses_iso_format(cls, value: object) -> object:
        if isinstance(value, date):
            return value
        if not isinstance(value, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
            raise ValueError("Date must use YYYY-MM-DD.")
        return value


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str | None
    role: Literal["student", "team_member"]


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["Bearer"] = "Bearer"
    expires_in: Literal[3600] = 3600
    user: UserResponse


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
    def timestamps_are_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class ItemPage(BaseModel):
    data: list[ItemResponse]
    limit: int
    offset: int
    total: int
