"""Supabase Data-Access Repository for SkillSetu.

Phase 32A: Established as the authoritative persistence layer for employer_feedback.
Eliminates reliance on in-memory _cache and JSON writes for migrated domains.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("skillsetu.repository.supabase")

_client_override: Any | None = None


class SupabaseRepositoryError(Exception):
    """Base exception for Supabase repository data-access failures."""
    pass


class FeedbackNotFoundError(SupabaseRepositoryError):
    """Raised when an employer feedback record does not exist in Supabase."""
    pass


class DemandNotFoundError(SupabaseRepositoryError):
    """Raised when an employer demand record does not exist in Supabase."""
    pass


class SupabaseConnectionError(SupabaseRepositoryError):
    """Raised when Supabase client is not configured or fails to connect."""
    pass


def set_supabase_client(client: Any | None) -> None:
    """Set a client override (useful for testing and dependency injection)."""
    global _client_override
    _client_override = client


def reset_supabase_client() -> None:
    """Reset the client override to default behavior."""
    global _client_override
    _client_override = None


def get_client() -> Any:
    """Retrieve active Supabase client or raise SupabaseConnectionError."""
    global _client_override
    if _client_override is not None:
        return _client_override

    from app.db import get_supabase_client
    client = get_supabase_client()
    if client is None:
        raise SupabaseConnectionError(
            "Supabase client is not configured or unavailable. Check SUPABASE_URL and credentials."
        )
    return client


# ============================================================================
# EMPLOYER FEEDBACK REPOSITORY DOMAIN (Phase 32A)
# ============================================================================

def get_employer_feedback(feedback_id: str) -> dict[str, Any] | None:
    """Query single employer feedback record by ID directly from Supabase."""
    try:
        client = get_client()
        res = client.table("employer_feedback").select("*").eq("id", feedback_id).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except SupabaseRepositoryError:
        raise
    except Exception as e:
        logger.error("[SupabaseRepo] Failed querying employer_feedback id='%s': %s", feedback_id, e)
        raise SupabaseRepositoryError(f"Database query failed for employer_feedback '{feedback_id}': {e}") from e


def list_employer_feedback(
    status: str | None = None,
    demand_level: str | None = None,
) -> list[dict[str, Any]]:
    """Query employer feedback records directly from Supabase with optional filtering."""
    try:
        client = get_client()
        query = client.table("employer_feedback").select("*")

        if status and status.lower() != "all":
            query = query.eq("status", status.lower())
        if demand_level and demand_level.lower() != "all":
            query = query.eq("demand_level", demand_level.lower())

        res = query.execute()
        return res.data or []
    except SupabaseRepositoryError:
        raise
    except Exception as e:
        logger.error("[SupabaseRepo] Failed listing employer_feedback: %s", e)
        raise SupabaseRepositoryError(f"Database query failed for employer_feedback list: {e}") from e


def update_employer_feedback(feedback_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    """Perform authoritative update on Supabase employer_feedback record.
    
    Returns the updated record on confirmed success.
    Raises FeedbackNotFoundError if no matching row was updated.
    Raises SupabaseRepositoryError on database failure.
    Does NOT write to local JSON files.
    Does NOT treat in-memory _cache as authoritative.
    """
    try:
        client = get_client()
        res = client.table("employer_feedback").update(updates).eq("id", feedback_id).execute()
        if not res.data or len(res.data) == 0:
            raise FeedbackNotFoundError(f"Employer feedback record '{feedback_id}' not found in Supabase.")
        
        updated_row = res.data[0]
        logger.info("[SupabaseRepo] Confirmed Supabase update for employer_feedback '%s' (status=%s)",
                    feedback_id, updated_row.get("status"))
        return updated_row
    except SupabaseRepositoryError:
        raise
    except Exception as e:
        logger.error("[SupabaseRepo] Failed updating employer_feedback id='%s': %s", feedback_id, e)
        raise SupabaseRepositoryError(f"Database update failed for employer_feedback '{feedback_id}': {e}") from e


# ============================================================================
# EMPLOYER DEMANDS REPOSITORY DOMAIN (Phase 32B)
# ============================================================================

def get_employer_demand(demand_id: str) -> dict[str, Any] | None:
    """Query single employer demand record by ID directly from Supabase."""
    try:
        client = get_client()
        res = client.table("employer_demands").select("*").eq("id", demand_id).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except SupabaseRepositoryError:
        raise
    except Exception as e:
        logger.error("[SupabaseRepo] Failed querying employer_demands id='%s': %s", demand_id, e)
        raise SupabaseRepositoryError(f"Database query failed for employer_demands '{demand_id}': {e}") from e


def list_employer_demands(
    employer_id: str | None = None,
    user_id: str | None = None,
    user_email: str | None = None,
    validation_status: str | None = None,
    district: str | None = None,
    is_demo: bool | None = None,
) -> list[dict[str, Any]]:
    """Query employer demand records directly from Supabase with optional filtering."""
    try:
        client = get_client()
        query = client.table("employer_demands").select("*")

        if employer_id:
            query = query.eq("employer_id", employer_id)
        if user_id:
            query = query.eq("user_id", user_id)
        if user_email:
            query = query.eq("user_email", user_email)
        if validation_status and validation_status.lower() != "all":
            query = query.eq("validation_status", validation_status.upper())
        if district and district.lower() != "all":
            query = query.eq("district", district)
        if is_demo is not None:
            query = query.eq("is_demo", is_demo)

        res = query.execute()
        return res.data or []
    except SupabaseRepositoryError:
        raise
    except Exception as e:
        logger.error("[SupabaseRepo] Failed listing employer_demands: %s", e)
        raise SupabaseRepositoryError(f"Database query failed for employer_demands list: {e}") from e


def create_employer_demand(demand_data: dict[str, Any]) -> dict[str, Any]:
    """Authoritatively insert an employer demand record into Supabase.

    Returns created demand record on success.
    Raises SupabaseRepositoryError on database failure.
    Does NOT write to local JSON.
    Does NOT treat in-memory _cache as authoritative.
    """
    try:
        client = get_client()
        res = client.table("employer_demands").insert(demand_data).execute()
        if not res.data or len(res.data) == 0:
            return demand_data
        created_row = res.data[0]
        logger.info("[SupabaseRepo] Confirmed Supabase insert for employer_demand '%s'", created_row.get("id"))
        return created_row
    except SupabaseRepositoryError:
        raise
    except Exception as e:
        logger.error("[SupabaseRepo] Failed inserting employer_demand: %s", e)
        raise SupabaseRepositoryError(f"Database insertion failed for employer_demand: {e}") from e


def update_employer_demand(demand_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    """Authoritatively update an employer demand record in Supabase.

    Returns updated demand record on success.
    Raises DemandNotFoundError if no matching row was updated.
    Raises SupabaseRepositoryError on database failure.
    Does NOT write to local JSON.
    Does NOT treat in-memory _cache as authoritative.
    """
    try:
        client = get_client()
        res = client.table("employer_demands").update(updates).eq("id", demand_id).execute()
        if not res.data or len(res.data) == 0:
            raise DemandNotFoundError(f"Employer demand record '{demand_id}' not found in Supabase.")
        updated_row = res.data[0]
        logger.info("[SupabaseRepo] Confirmed Supabase update for employer_demand '%s'", demand_id)
        return updated_row
    except SupabaseRepositoryError:
        raise
    except Exception as e:
        logger.error("[SupabaseRepo] Failed updating employer_demand id='%s': %s", demand_id, e)
        raise SupabaseRepositoryError(f"Database update failed for employer_demand '{demand_id}': {e}") from e


def delete_employer_demand_repo(demand_id: str) -> bool:
    """Authoritatively delete an employer demand record from Supabase."""
    try:
        client = get_client()
        client.table("employer_demands").delete().eq("id", demand_id).execute()
        logger.info("[SupabaseRepo] Confirmed Supabase deletion for employer_demand '%s'", demand_id)
        return True
    except SupabaseRepositoryError:
        raise
    except Exception as e:
        logger.error("[SupabaseRepo] Failed deleting employer_demand id='%s': %s", demand_id, e)
        raise SupabaseRepositoryError(f"Database deletion failed for employer_demand '{demand_id}': {e}") from e
