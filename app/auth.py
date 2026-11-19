from dataclasses import dataclass

from fastapi import Header

from app.errors import ApiError, ErrorCode

ROLE_USER = "user"
ROLE_ADMIN = "admin"


@dataclass(frozen=True)
class User:
    id: str
    name: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN


USERS = {
    "user-a": User(id="user-a", name="Demo User A", role=ROLE_USER),
    "user-b": User(id="user-b", name="Demo User B", role=ROLE_USER),
    "admin": User(id="admin", name="Administrator", role=ROLE_ADMIN),
}

TOKENS = {
    "user-a-token": "user-a",
    "user-b-token": "user-b",
    "admin-token": "admin",
}

_WWW_AUTH = {"WWW-Authenticate": "Bearer"}


def get_current_user(
    authorization: str | None = Header(
        default=None,
        description="Bearer token: user-a-token, user-b-token or admin-token.",
    ),
) -> User:
    """FastAPI dependency: answers *who is making the request?* or raises 401."""
    if authorization is None or not authorization.strip():
        raise ApiError(
            401,
            ErrorCode.UNAUTHORIZED,
            "Authentication required. Send the header 'Authorization: Bearer <token>'.",
            headers=_WWW_AUTH,
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise ApiError(
            401,
            ErrorCode.INVALID_TOKEN,
            "The Authorization header must have the format 'Bearer <token>'.",
            headers=_WWW_AUTH,
        )

    user_id = TOKENS.get(parts[1])
    if user_id is None:
        raise ApiError(401, ErrorCode.INVALID_TOKEN, "The access token is invalid or has expired.", headers=_WWW_AUTH)
    return USERS[user_id]


def can_access(user: User, meal: dict) -> bool:
    """Answers *is this user allowed to touch this meal?* Admins can touch everything."""
    return user.is_admin or meal["ownerId"] == user.id
