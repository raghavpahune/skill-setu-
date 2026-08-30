"""Authentication API — registration, login, profile retrieval, and session management."""
from datetime import datetime, timezone
import uuid
import re
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from app.db import get_user_by_email, get_user_by_id, save_user

router = APIRouter()

ALLOWED_PUBLIC_ROLES = {"STUDENT", "EMPLOYER", "INSTITUTE", "GOVERNMENT"}
ALL_ROLES = {"STUDENT", "EMPLOYER", "INSTITUTE", "GOVERNMENT", "ADMIN"}


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=150, description="Valid email address")
    password: str = Field(..., min_length=6, max_length=100, description="Minimum 6 characters password")
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name")
    role: str = Field(..., description="STUDENT, EMPLOYER, INSTITUTE, or GOVERNMENT")
    organization_id: str | None = None
    district: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean):
            raise ValueError("Invalid email format")
        return clean

    @field_validator("role")
    @classmethod
    def validate_role_field(cls, v: str) -> str:
        clean = v.strip().upper()
        if clean == "ADMIN":
            raise ValueError("Public registration for ADMIN role is not permitted")
        if clean not in ALLOWED_PUBLIC_ROLES:
            raise ValueError(f"Invalid role '{v}'. Allowed roles: {list(ALLOWED_PUBLIC_ROLES)}")
        return clean

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v.strip()) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=150)
    password: str = Field(..., min_length=1, max_length=100)


def sanitize_user(user: dict[str, Any]) -> dict[str, Any]:
    """Return user dictionary excluding sensitive hash fields."""
    return {
        "id": user.get("id"),
        "email": user.get("email"),
        "full_name": user.get("full_name"),
        "role": user.get("role"),
        "organization_id": user.get("organization_id"),
        "district": user.get("district"),
        "is_active": user.get("is_active", True),
        "created_at": user.get("created_at"),
        "updated_at": user.get("updated_at"),
    }


@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest):
    """Register a new user account with role-based identity."""
    existing = get_user_by_email(req.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An account with email '{req.email}' already exists",
        )

    user_id = f"usr-{req.role.lower()}-{uuid.uuid4().hex[:8]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    new_user = {
        "id": user_id,
        "email": req.email,
        "hashed_password": hash_password(req.password),
        "full_name": req.full_name.strip(),
        "role": req.role,
        "organization_id": req.organization_id.strip() if req.organization_id else None,
        "district": req.district.strip() if req.district else None,
        "is_active": True,
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    saved = save_user(new_user)
    token = create_access_token({
        "sub": saved["id"],
        "email": saved["email"],
        "role": saved["role"],
        "name": saved["full_name"],
    })

    return {
        "status": "success",
        "message": "User account registered successfully",
        "access_token": token,
        "token_type": "bearer",
        "user": sanitize_user(saved),
    }


@router.post("/auth/login")
async def login(req: LoginRequest):
    """Authenticate with email and password to receive a JWT bearer token."""
    clean_email = req.email.strip().lower()
    user = get_user_by_email(clean_email)

    if not user or not verify_password(req.password, user.get("hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Contact platform administrator.",
        )

    token = create_access_token({
        "sub": user["id"],
        "email": user["email"],
        "role": user["role"],
        "name": user.get("full_name", ""),
    })

    return {
        "status": "success",
        "access_token": token,
        "token_type": "bearer",
        "user": sanitize_user(user),
    }


@router.get("/auth/me")
async def get_me(current_user: dict[str, Any] = Depends(get_current_user)):
    """Retrieve profile of the currently authenticated user."""
    return {
        "status": "success",
        "user": sanitize_user(current_user),
    }


@router.post("/auth/logout")
async def logout():
    """Sign out the current session."""
    return {
        "status": "success",
        "message": "Successfully logged out",
    }
