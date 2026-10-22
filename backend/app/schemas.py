from datetime import date, datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


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
        return value.astimezone(timezone.utc)


class ItemPage(BaseModel):
    data: list[ItemResponse]
    limit: int
    offset: int
    total: int
