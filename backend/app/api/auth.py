from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_auth_settings, verify_google_token
from app.database import Settings, get_db
from app.errors import APIError
from app.models import User
from app.schemas import LoginRequest, LoginResponse, UserResponse

router = APIRouter()


def require_json(request: Request) -> None:
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
        raise APIError(415, "UNSUPPORTED_MEDIA_TYPE", "Content-Type must be application/json.")


@router.post("/auth/google", response_model=LoginResponse, operation_id="loginWithGoogle",
             dependencies=[Depends(require_json)])
def login_with_google(
    body: LoginRequest,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_auth_settings)],
) -> LoginResponse:
    identity = verify_google_token(body.id_token, settings)
    # Concurrent/repeated logins share one user; manual role assignments survive login.
    statement = insert(User).values(
        id=uuid4(), google_sub=identity.sub, email=identity.email,
        name=identity.name, role="student",
    ).on_conflict_do_update(
        index_elements=[User.google_sub],
        set_={"email": identity.email, "name": identity.name},
    ).returning(User)
    user = db.scalars(statement, execution_options={"populate_existing": True}).one()
    token = create_access_token(user.id, settings)
    profile = UserResponse.model_validate(user)
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return LoginResponse(access_token=token, user=profile)
