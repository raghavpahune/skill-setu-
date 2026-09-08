"""Authentication API — registration, login, profile retrieval, and session management."""
from datetime import datetime, timezone
import asyncio
import os
import uuid
import re
import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from app.db import (
    get_user_by_email,
    get_user_by_id,
    save_user,
    get_supabase_client,
    NON_ADMIN_DEMO_EMAILS,
)

logger = logging.getLogger("skillsetu.auth")
router = APIRouter()

ALLOWED_PUBLIC_ROLES = {"STUDENT", "EMPLOYEE", "EMPLOYER", "INSTITUTE", "GOVERNMENT"}
ALL_ROLES = {"STUDENT", "EMPLOYEE", "EMPLOYER", "INSTITUTE", "GOVERNMENT", "ADMIN"}


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=150, description="Valid email address")
    password: str = Field(..., min_length=6, max_length=100, description="Minimum 6 characters password")
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name")
    role: str = Field(..., description="STUDENT, EMPLOYEE, EMPLOYER, INSTITUTE, or GOVERNMENT")
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

    try:
        saved = save_user(new_user)
    except Exception as e:
        logger.exception("[Auth] Failed persisting user: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database persistence failed for user registration.",
        ) from e
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
    clean_email = req.email.strip().lower()
    client = get_supabase_client()
    user = None
    authenticated = False
    auth_uid = None
    auth_role = None

    if client is not None and hasattr(client, "auth") and hasattr(client.auth, "sign_in_with_password"):
        try:
            auth_resp = await asyncio.wait_for(
                asyncio.to_thread(
                    client.auth.sign_in_with_password,
                    {"email": clean_email, "password": req.password},
                ),
                timeout=5.0,
            )
            if auth_resp and getattr(auth_resp, "user", None):
                sb_user = auth_resp.user
                auth_uid = str(sb_user.id)
                authenticated = True
        except Exception as e:
            logger.debug("[Auth] Supabase GoTrue authentication error: %s", e)

        if not authenticated and not settings.is_production and settings.demo_auth_enabled and clean_email == "admin@skillsetu.gov.in" and hasattr(client.auth, "admin"):
            expected_admin_password = getattr(settings, "admin_password", "") or os.getenv("ADMIN_PASSWORD") or "AdminPass@2026"
            if req.password == expected_admin_password:
                try:
                    resolved_admin_id = None
                    page = 1
                    while page <= 20:
                        try:
                            auth_users_resp = await asyncio.wait_for(
                                asyncio.to_thread(client.auth.admin.list_users, page=page, per_page=100),
                                timeout=5.0,
                            )
                        except TypeError:
                            auth_users_resp = await asyncio.wait_for(
                                asyncio.to_thread(client.auth.admin.list_users),
                                timeout=5.0,
                            )
                            page_users = getattr(auth_users_resp, "users", None) or (auth_users_resp if isinstance(auth_users_resp, list) else [])
                            matched_u = next(
                                (u for u in page_users if str(getattr(u, "email", "")).strip().lower() == clean_email),
                                None,
                            )
                            if matched_u and getattr(matched_u, "id", None):
                                resolved_admin_id = str(matched_u.id)
                            break
                        page_users = getattr(auth_users_resp, "users", None) or (auth_users_resp if isinstance(auth_users_resp, list) else [])
                        if not page_users:
                            break
                        matched_u = next(
                            (u for u in page_users if str(getattr(u, "email", "")).strip().lower() == clean_email),
                            None,
                        )
                        if matched_u and getattr(matched_u, "id", None):
                            resolved_admin_id = str(matched_u.id)
                            break
                        if len(page_users) < 100:
                            break
                        page += 1

                    if resolved_admin_id:
                        await asyncio.wait_for(
                            asyncio.to_thread(
                                client.auth.admin.update_user_by_id,
                                resolved_admin_id,
                                {
                                    "password": req.password,
                                    "email_confirm": True,
                                    "user_metadata": {
                                        "role": "ADMIN",
                                        "name": "SkillSetu System Administrator",
                                    },
                                },
                            ),
                            timeout=5.0,
                        )
                        retry_auth_resp = await asyncio.wait_for(
                            asyncio.to_thread(
                                client.auth.sign_in_with_password,
                                {"email": clean_email, "password": req.password},
                            ),
                            timeout=5.0,
                        )
                        if retry_auth_resp and getattr(retry_auth_resp, "user", None):
                            sb_user = retry_auth_resp.user
                            auth_uid = str(sb_user.id)
                            authenticated = True
                except Exception as sync_err:
                    logger.warning("[Auth] GoTrue admin password sync retry error: %s", sync_err)

        if authenticated and auth_uid:
            if clean_email == "admin@skillsetu.gov.in":
                if settings.is_production:
                    try:
                        db_role_res = await asyncio.wait_for(
                            asyncio.to_thread(
                                lambda: client.table("users").select("role").eq("id", auth_uid).execute()
                            ),
                            timeout=5.0,
                        )
                        db_rows = getattr(db_role_res, "data", None) or []
                        if db_rows:
                            r_val = str(db_rows[0].get("role", "")).strip().upper()
                            if r_val != "ADMIN":
                                raise HTTPException(
                                    status_code=status.HTTP_403_FORBIDDEN,
                                    detail="Forbidden: Admin role required.",
                                )
                    except HTTPException:
                        raise
                    except Exception as db_err:
                        logger.error("[Auth] Database role lookup failed for admin %s: %s", auth_uid, db_err)
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Database error while resolving authoritative user permissions.",
                        ) from db_err
                auth_role = "ADMIN"
            else:
                try:
                    db_role_res = await asyncio.wait_for(
                        asyncio.to_thread(
                            lambda: client.table("users").select("role").eq("id", auth_uid).execute()
                        ),
                        timeout=5.0,
                    )
                except Exception as db_err:
                    logger.error("[Auth] Database role lookup failed for uid %s: %s", auth_uid, db_err)
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Database error while resolving authoritative user permissions.",
                    ) from db_err

                db_rows = getattr(db_role_res, "data", None) or []
                if not db_rows:
                    logger.warning("[Auth] No authoritative role found in public.users for uid %s", auth_uid)
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Forbidden: No authoritative role assigned to this account.",
                    )
                assigned_role = str(db_rows[0].get("role", "")).strip().upper()
                if assigned_role not in ALLOWED_PUBLIC_ROLES:
                    logger.warning("[Auth] Invalid or unauthorized role '%s' for uid %s", assigned_role, auth_uid)
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Forbidden: Insufficient or unauthorized role.",
                    )
                auth_role = assigned_role

            meta = getattr(sb_user, "user_metadata", {}) or {}
            display_name = meta.get("full_name") or meta.get("name") or (
                "SkillSetu System Administrator" if auth_role == "ADMIN" else clean_email.split("@")[0]
            )
            user = {
                "id": auth_uid,
                "email": clean_email,
                "role": auth_role,
                "full_name": display_name,
                "name": display_name,
                "is_active": True,
            }

            try:
                await asyncio.wait_for(
                    asyncio.to_thread(save_user, user),
                    timeout=5.0,
                )
            except Exception as persistence_err:
                logger.exception("[Auth] Failed reconciling user %s in public.users: %s", clean_email, persistence_err)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"User account reconciliation failed. Database persistence error: {persistence_err}",
                ) from persistence_err

        elif not authenticated:
            if clean_email == "admin@skillsetu.gov.in":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            if not settings.is_production and settings.demo_auth_enabled and clean_email in NON_ADMIN_DEMO_EMAILS:
                demo_user = get_user_by_email(clean_email)
                if demo_user and demo_user.get("hashed_password") and verify_password(req.password, demo_user.get("hashed_password", "")):
                    user = demo_user
                    authenticated = True
            else:
                db_user = get_user_by_email(clean_email)
                if db_user and db_user.get("hashed_password") and verify_password(req.password, db_user.get("hashed_password", "")):
                    user = db_user
                    authenticated = True

    if not authenticated:
        cached_user = get_user_by_email(clean_email)
        if cached_user and cached_user.get("hashed_password") and verify_password(req.password, cached_user.get("hashed_password", "")):
            if clean_email == "admin@skillsetu.gov.in":
                if not settings.is_production and settings.demo_auth_enabled:
                    user = cached_user
                    user["role"] = "ADMIN"
                    authenticated = True
            elif cached_user.get("is_demo") or clean_email in NON_ADMIN_DEMO_EMAILS:
                if not settings.is_production and settings.demo_auth_enabled:
                    user = cached_user
                    authenticated = True
            else:
                user = cached_user
                authenticated = True

    if not authenticated or not user:
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
        "name": user.get("full_name") or user.get("name", ""),
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
