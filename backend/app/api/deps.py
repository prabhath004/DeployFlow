from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import decode_access_token
from app.db.database import get_session
from app.db.redis import get_redis
from app.models.user import User
from app.repositories.user_repo import UserRepo

# tokenUrl powers the "Authorize" button in Swagger UI; the path is informational.
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
RedisDep = Annotated[Redis, Depends(get_redis)]


async def get_current_user(
    token: Annotated[str, Depends(_oauth2_scheme)],
    session: SessionDep,
    settings: SettingsDep,
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token, settings)
        user_id = payload.get("sub")
        if not isinstance(user_id, str):
            raise credentials_exc
    except jwt.InvalidTokenError as exc:
        raise credentials_exc from exc

    user = await UserRepo(session).get_by_id(user_id)
    if user is None:
        raise credentials_exc
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def ensure_owner(resource_user_id: str, current_user: User) -> None:
    """Phase 4 will use this in project/deployment routes.

    Raises 404 (not 403) when ownership doesn't match so we don't leak
    the existence of resources to other users.
    """
    if resource_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
        )
