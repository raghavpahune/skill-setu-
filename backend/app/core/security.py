"""Security module — password hashing, JWT token creation/verification, and FastAPI RBAC dependencies."""
from datetime import datetime, timedelta, timezone
from typing import Any
import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

# HTTP Bearer scheme
bearer_scheme = HTTPBearer(auto_error=False)

DEFAULT_DEMO_ADMIN_KEY = "demo-admin-key-2026"


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token."""
    secret = (settings.jwt_secret_key or "").strip()
    if not secret:
        raise RuntimeError("JWT_SECRET_KEY is mandatory and not configured. Refusing to issue token with an insecure default.")

    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.jwt_expire_minutes)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "nbf": now,
    })
    encoded_jwt = jwt.encode(
        to_encode,
        secret,
        algorithm=settings.jwt_algorithm,
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT access token."""
    secret = (settings.jwt_secret_key or "").strip()
    if not secret:
        raise RuntimeError("JWT_SECRET_KEY is mandatory and not configured. Refusing to validate token with an insecure default.")

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except jwt.PyJWTError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    """FastAPI dependency to extract and verify the current authenticated user from Bearer token."""
    from app.db import get_user_by_id, get_user_by_email

    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: missing or invalid Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    email = payload.get("email")
    if not user_id and not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_id(user_id) if user_id else get_user_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return user


async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any] | None:
    """FastAPI dependency that returns the current user if a valid token is present, else None."""
    if not credentials or not credentials.credentials:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def require_roles(allowed_roles: list[str]):
    """FastAPI dependency factory enforcing that current_user has one of the allowed roles."""
    normalized_allowed = {r.upper() for r in allowed_roles}

    async def role_checker(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        user_role = (current_user.get("role") or "").upper()
        if user_role not in normalized_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Insufficient role permissions. Required one of: {list(normalized_allowed)}",
            )
        return current_user

    return role_checker


async def verify_admin_access(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> dict[str, Any] | bool:
    """Enforce admin authorization:

    1. If a Bearer token is provided, verify valid JWT and check user.role == 'ADMIN'.
       If the token is valid for a non-admin role (e.g. STUDENT), raise 403 Forbidden.
    2. If no Bearer token is provided, check if X-Admin-Key matches configured key or demo fallback (when demo_auth_enabled).
    3. Otherwise raise 401 Unauthorized.
    """
    # 1. Bearer Token Auth (Primary Production Method)
    if credentials and credentials.credentials:
        token = credentials.credentials
        payload = decode_access_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired admin access token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        from app.db import get_user_by_id, get_user_by_email
        user_id = payload.get("sub")
        email = payload.get("email")
        user = get_user_by_id(user_id) if user_id else get_user_by_email(email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin user account not found",
            )

        user_role = (user.get("role") or "").upper()
        if user_role != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Admin role required to access this resource",
            )
        return user

    # 2. X-Admin-Key Auth (Configured Secret or Demo Fallback)
    expected_key = settings.admin_api_key.strip() if (settings.admin_api_key and settings.admin_api_key.strip()) else (DEFAULT_DEMO_ADMIN_KEY if settings.demo_auth_enabled else "")
    if expected_key and x_admin_key and x_admin_key.strip() == expected_key:
        return True

    # 3. Reject if neither valid Bearer token nor valid Admin Key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized: Admin authorization required (provide Bearer token with ADMIN role or valid X-Admin-Key)",
        headers={"WWW-Authenticate": "Bearer"},
    )


def is_demo_student_id(student_id: str | None) -> bool:
    """Check whether a student ID explicitly belongs to an approved demo persona.

    Recognizes ONLY explicitly demo-prefixed IDs:
        - ast-demo-*
        - demo-*

    Crucially, generic prefixes like 'stu-*' are NEVER recognized as demo identifiers.
    This prevents real or non-demo students whose IDs happen to begin with 'stu-'
    from receiving demo job fixtures or being routed into demo computations.
    """
    if not student_id or not isinstance(student_id, str):
        return False
    # ponytail: strictly match demo prefixes only, never generic stu-*
    return student_id.startswith(("ast-demo-", "demo-"))
