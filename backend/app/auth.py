from datetime import datetime, timedelta, timezone
from functools import partial
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.exceptions import GoogleAuthError, TransportError
from google.auth.transport.requests import Request
from google.oauth2 import id_token
import jwt
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import Settings, get_db
from app.errors import APIError
from app.models import User

bearer = HTTPBearer(auto_error=False)


def get_auth_settings() -> Settings:
    settings = Settings()
    # Keep listing/setup usable before Google configuration is supplied.
    if not settings.google_client_id.strip() or len(settings.auth_secret_key.get_secret_value().encode()) < 32:
        raise APIError(500, "INTERNAL_ERROR", "Authentication is not configured.")
    return settings


class GoogleIdentity(BaseModel):
    sub: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=1, max_length=320)
    email_verified: bool = Field(strict=True)
    name: str | None = None


def verify_google_token(token: str, settings: Settings) -> GoogleIdentity:
    try:
        claims = id_token.verify_oauth2_token(
            token, partial(Request(), timeout=5), audience=settings.google_client_id,
        )
        identity = GoogleIdentity.model_validate(claims)
        if not identity.email_verified:
            raise ValueError("Unverified email")
        return identity
    except TransportError:
        raise APIError(503, "AUTH_PROVIDER_UNAVAILABLE", "Google authentication is temporarily unavailable.") from None
    except (ValueError, GoogleAuthError):
        raise APIError(401, "INVALID_GOOGLE_TOKEN", "Invalid Google ID token.") from None


def create_access_token(user_id: UUID, settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": str(user_id), "iss": "lostandfound", "iat": now, "exp": now + timedelta(hours=1)},
        settings.auth_secret_key.get_secret_value(), algorithm="HS256",
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_auth_settings)],
) -> User:
    error = APIError(401, "UNAUTHENTICATED", "A valid bearer token is required.",
                     headers={"WWW-Authenticate": "Bearer"})
    if credentials is None:
        raise error
    try:
        claims = jwt.decode(
            credentials.credentials, settings.auth_secret_key.get_secret_value(),
            algorithms=["HS256"], issuer="lostandfound",
            options={"require": ["sub", "iss", "iat", "exp"]},
        )
        user_id = UUID(claims["sub"])
    except (jwt.InvalidTokenError, ValueError):
        raise error from None
    user = db.get(User, user_id)
    if user is None:
        raise error
    return user
