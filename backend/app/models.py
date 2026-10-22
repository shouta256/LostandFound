from datetime import date, datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        CheckConstraint("type IN ('lost', 'found')", name="ck_items_type"),
        CheckConstraint("status IN ('available', 'claimed', 'returned')", name="ck_items_status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(5))
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(2000))
    category: Mapped[str] = mapped_column(String(80))
    date: Mapped[date]
    location: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(9), default="available")
    # User persistence will be added with Google authentication.
    created_by: Mapped[UUID]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
