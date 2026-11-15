from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth import require_json
from app.auth import get_current_user, require_team_member
from app.database import get_db
from app.errors import APIError
from app.models import Claim, Item, Pickup, User
from app.schemas import ClaimCreate, ClaimDecision, ClaimDetailResponse, ClaimPage, ClaimResponse, PickupResponse, PickupUpdate

router = APIRouter()


def _claim_or_404(db: Session, claim_id: UUID) -> Claim:
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise APIError(404, "CLAIM_NOT_FOUND", "Claim not found.")
    return claim


@router.post("/claims", response_model=ClaimResponse, status_code=201, operation_id="createClaim",
             dependencies=[Depends(require_json)])
def create_claim(body: ClaimCreate, db: Annotated[Session, Depends(get_db)],
                 user: Annotated[User, Depends(get_current_user)], response: Response) -> ClaimResponse:
    item = db.get(Item, body.item_id)
    if item is None:
        raise APIError(404, "ITEM_NOT_FOUND", "Item not found.")
    if item.created_by == user.id:
        raise APIError(403, "FORBIDDEN", "You cannot claim your own listing.")
    if item.type != "found" or item.status != "available":
        raise APIError(409, "ITEM_NOT_CLAIMABLE", "This item is not available for claims.")
    pending_claim = db.scalar(select(Claim.id).where(
        Claim.item_id == item.id,
        Claim.claimant_id == user.id,
        Claim.status == "pending",
    ))
    if pending_claim is not None:
        raise APIError(409, "DUPLICATE_PENDING_CLAIM", "A pending claim already exists for this item.")
    now = datetime.now(timezone.utc)
    claim = Claim(id=uuid4(), item_id=item.id, claimant_id=user.id,
                  ownership_information=body.ownership_information, status="pending",
                  reviewed_by=None, reviewed_at=None, created_at=now, updated_at=now)
    db.add(claim)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise APIError(409, "DUPLICATE_PENDING_CLAIM", "A pending claim already exists for this item.") from None
    db.refresh(claim)
    response.headers["Location"] = f"/api/v1/claims/{claim.id}"
    response.headers["Cache-Control"] = "no-store"
    return ClaimResponse.model_validate(claim)


@router.get("/claims", response_model=ClaimPage, operation_id="listClaims")
def list_claims(db: Annotated[Session, Depends(get_db)], user: Annotated[User, Depends(get_current_user)],
                response: Response,
                limit: Annotated[int, Query(ge=1, le=100)] = 20,
                offset: Annotated[int, Query(ge=0)] = 0) -> ClaimPage:
    condition = True if user.role == "team_member" else Claim.claimant_id == user.id
    total = db.scalar(select(func.count()).select_from(Claim).where(condition)) or 0
    claims = db.scalars(select(Claim).where(condition).order_by(
        Claim.created_at.desc(), Claim.id.desc()).limit(limit).offset(offset)).all()
    response.headers["Cache-Control"] = "no-store"
    return ClaimPage(data=claims, total=total, limit=limit, offset=offset)


@router.get("/claims/{claim_id}", response_model=ClaimDetailResponse, operation_id="getClaim")
def get_claim(claim_id: UUID, db: Annotated[Session, Depends(get_db)],
              user: Annotated[User, Depends(get_current_user)], response: Response) -> ClaimDetailResponse:
    claim = _claim_or_404(db, claim_id)
    if user.role != "team_member" and claim.claimant_id != user.id:
        raise APIError(403, "FORBIDDEN", "This claim is not accessible to you.")
    pickup = claim.pickup if claim.status == "approved" else None
    response.headers["Cache-Control"] = "no-store"
    return ClaimDetailResponse.model_validate({**ClaimResponse.model_validate(claim).model_dump(),
        "pickup": PickupResponse.model_validate(pickup) if pickup else None})


@router.patch("/claims/{claim_id}/decision", response_model=ClaimResponse, operation_id="decideClaim",
              dependencies=[Depends(require_json)])
def decide_claim(claim_id: UUID, body: ClaimDecision, db: Annotated[Session, Depends(get_db)],
                 user: Annotated[User, Depends(require_team_member)], response: Response) -> ClaimResponse:
    claim = db.scalar(select(Claim).where(Claim.id == claim_id).with_for_update())
    if claim is None:
        raise APIError(404, "CLAIM_NOT_FOUND", "Claim not found.")
    if claim.claimant_id == user.id:
        raise APIError(403, "FORBIDDEN", "Team members cannot review their own claims.")
    if claim.status != "pending":
        if claim.status == body.status:
            response.headers["Cache-Control"] = "no-store"
            return ClaimResponse.model_validate(claim)
        raise APIError(409, "CLAIM_ALREADY_DECIDED", "This claim has already been decided.")
    if body.status == "approved":
        item = db.scalar(select(Item).where(Item.id == claim.item_id).with_for_update())
        if item.type != "found" or item.status != "available":
            raise APIError(409, "CLAIM_APPROVAL_CONFLICT", "The item is no longer available.")
        item.status = "claimed"
        item.updated_at = datetime.now(timezone.utc)
    now = datetime.now(timezone.utc)
    claim.status = body.status
    claim.reviewed_by = user.id
    claim.reviewed_at = now
    claim.updated_at = now
    db.commit()
    db.refresh(claim)
    response.headers["Cache-Control"] = "no-store"
    return ClaimResponse.model_validate(claim)


@router.patch("/claims/{claim_id}/pickup", response_model=PickupResponse, operation_id="updateClaimPickup",
              dependencies=[Depends(require_json)])
def update_claim_pickup(claim_id: UUID, body: PickupUpdate, db: Annotated[Session, Depends(get_db)],
                        _user: Annotated[User, Depends(require_team_member)], response: Response) -> PickupResponse:
    claim = db.scalar(select(Claim).where(Claim.id == claim_id).with_for_update())
    if claim is None:
        raise APIError(404, "CLAIM_NOT_FOUND", "Claim not found.")
    if claim.status != "approved":
        raise APIError(409, "CLAIM_NOT_APPROVED", "Pickup can only be set for approved claims.")
    pickup = db.get(Pickup, claim.id)
    now = datetime.now(timezone.utc)
    ready_at = now if body.status == "ready" and (pickup is None or pickup.status != "ready") else (
        pickup.ready_at if pickup and body.status == "ready" else None)
    if pickup is None:
        pickup = Pickup(claim_id=claim.id, location=body.location, status=body.status, ready_at=ready_at)
        db.add(pickup)
    else:
        pickup.location, pickup.status, pickup.ready_at = body.location, body.status, ready_at
    db.commit()
    db.refresh(pickup)
    response.headers["Cache-Control"] = "no-store"
    return PickupResponse.model_validate(pickup)
