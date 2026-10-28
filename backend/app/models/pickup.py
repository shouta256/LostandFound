"""Optional campus pickup information for an approved ownership claim."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from ..database import Base
from .claim import Claim


class Pickup(Base):
    __tablename__ = "pickups"
    __table_args__ = (
        CheckConstraint(
            "length(trim(location)) >= 1 AND length(location) <= 200",
            name="ck_pickups_location_length",
        ),
        CheckConstraint(
            "status IN ('not_ready', 'ready')", name="ck_pickups_status"
        ),
        CheckConstraint(
            "(status = 'ready' AND ready_at IS NOT NULL) OR "
            "(status = 'not_ready' AND ready_at IS NULL)",
            name="ck_pickups_readiness_time",
        ),
    )

    # The claim UUID also identifies its pickup, enforcing at most one per claim.
    claim_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("claims.id"), primary_key=True
    )
    location: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="not_ready", server_default="not_ready"
    )
    # Future server workflow code sets/preserves/clears this when readiness changes.
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    claim: Mapped[Claim] = relationship(Claim, back_populates="pickup")

    @validates("location")
    def validate_location(self, key: str, value: str) -> str:
        value = value.strip()
        if not 1 <= len(value) <= 200:
            raise ValueError("location must contain 1 to 200 characters")
        return value
