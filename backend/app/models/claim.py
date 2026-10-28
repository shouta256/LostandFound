"""Private ownership claims and their review records."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from ..database import Base
from .item import Item, utc_now
from .user import User

if TYPE_CHECKING:
    from .pickup import Pickup


class Claim(Base):
    __tablename__ = "claims"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')", name="ck_claims_status"
        ),
        CheckConstraint(
            "length(trim(ownership_information)) >= 1 "
            "AND length(ownership_information) <= 2000",
            name="ck_claims_ownership_length",
        ),
        CheckConstraint(
            "(status = 'pending' AND reviewed_by IS NULL AND reviewed_at IS NULL) OR "
            "(status IN ('approved', 'rejected') "
            "AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)",
            name="ck_claims_review_information",
        ),
        CheckConstraint(
            "reviewed_by IS NULL OR reviewed_by != claimant_id",
            name="ck_claims_no_self_review",
        ),
        Index(
            "uq_claims_pending_user_item", "item_id", "claimant_id", unique=True,
            postgresql_where=text("status = 'pending'"),
            sqlite_where=text("status = 'pending'"),
        ),
        Index(
            "uq_claims_approved_item", "item_id", unique=True,
            postgresql_where=text("status = 'approved'"),
            sqlite_where=text("status = 'approved'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    item_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("items.id"), nullable=False)
    claimant_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    ownership_information: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="pending", server_default="pending"
    )
    reviewed_by: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now,
        server_default=func.now(), onupdate=utc_now,
    )

    item: Mapped[Item] = relationship(Item)
    claimant: Mapped[User] = relationship(User, foreign_keys=[claimant_id])
    reviewer: Mapped[User | None] = relationship(User, foreign_keys=[reviewed_by])
    pickup: Mapped["Pickup | None"] = relationship("Pickup", back_populates="claim")

    @validates("ownership_information")
    def validate_ownership_information(self, key: str, value: str) -> str:
        value = value.strip()
        if not 1 <= len(value) <= 2000:
            raise ValueError("ownership_information must contain 1 to 2000 characters")
        return value
