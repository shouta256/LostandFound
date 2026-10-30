from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('student', 'team_member')", name="ck_users_role"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    google_sub: Mapped[str] = mapped_column(String(255), unique=True)
    email: Mapped[str] = mapped_column(String(320))
    name: Mapped[str | None]
    role: Mapped[str] = mapped_column(String(11), default="student")


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
    created_by: Mapped[UUID]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


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
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        server_default=func.now(), onupdate=lambda: datetime.now(timezone.utc),
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
