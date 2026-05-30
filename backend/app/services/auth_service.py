from datetime import datetime

from app.core.config import Settings
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repo import UserRepo


class AuthError(Exception):
    """Raised for any auth-layer error; routes translate to HTTPException."""


class EmailAlreadyRegisteredError(AuthError): ...
class InvalidCredentialsError(AuthError): ...


class AuthService:
    def __init__(self, user_repo: UserRepo, settings: Settings) -> None:
        self.user_repo = user_repo
        self.settings = settings

    async def register(self, *, email: str, password: str) -> User:
        existing = await self.user_repo.get_by_email(email)
        if existing is not None:
            raise EmailAlreadyRegisteredError()
        return await self.user_repo.create(
            email=email, password_hash=hash_password(password)
        )

    async def login(self, *, email: str, password: str) -> tuple[str, datetime, User]:
        user = await self.user_repo.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()
        token, expires_at = create_access_token(
            subject=user.id, settings=self.settings
        )
        return token, expires_at, user
