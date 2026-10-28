"""Lost and found listings stored using the shared SQLAlchemy base."""

from datetime import date as DateValue, datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from ..database import Base
from .user import User


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        CheckConstraint("type IN ('lost', 'found')", name="ck_items_type"),
        CheckConstraint(
            "status IN ('available', 'claimed', 'returned')", name="ck_items_status"
        ),
        CheckConstraint(
            "type != 'lost' OR status != 'claimed'", name="ck_items_lost_status"
        ),
        CheckConstraint(
            "length(trim(name)) >= 1 AND length(name) <= 120",
            name="ck_items_name_length",
        ),
        CheckConstraint(
            "length(trim(description)) >= 1 AND length(description) <= 2000",
            name="ck_items_description_length",
        ),
        CheckConstraint(
            "length(trim(category)) >= 1 AND length(category) <= 80",
            name="ck_items_category_length",
        ),
        CheckConstraint(
            "length(trim(location)) >= 1 AND length(location) <= 200",
            name="ck_items_location_length",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[DateValue] = mapped_column(Date, nullable=False)
    location: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="available", server_default="available"
    )
    created_by: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False
    )
    creator: Mapped[User] = relationship(User)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now,
        server_default=func.now(), onupdate=utc_now,
    )

    @validates("name", "description", "category", "location")
    def validate_text(self, key: str, value: str) -> str:
        limits = {"name": 120, "description": 2000, "category": 80, "location": 200}
        value = value.strip()
        if not 1 <= len(value) <= limits[key]:
            raise ValueError(f"{key} must contain 1 to {limits[key]} characters")
        return value
