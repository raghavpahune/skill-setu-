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


class AssessmentNotFoundError(SupabaseRepositoryError):
    """Raised when a student assessment record cannot be located in Supabase."""
    pass


class ProfileNotFoundError(SupabaseRepositoryError):
    """Raised when a student profile record cannot be located in Supabase."""
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


# ===========================================================================
# STUDENT PROFILES
# ===========================================================================

def get_student_profile(user_id: str) -> dict[str, Any] | None:
    """Retrieve student profile directly from Supabase by user_id.

    Returns None if profile not found.
    Raises SupabaseRepositoryError on database failure.
    """
    try:
        client = get_client()
        res = client.table("student_profiles").select("*").eq("user_id", user_id).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        # Also check id column if present
        res_id = client.table("student_profiles").select("*").eq("id", user_id).execute()
        if res_id.data and len(res_id.data) > 0:
            return res_id.data[0]
        return None
    except Exception as e:
        logger.error("[SupabaseRepo] Failed fetching student_profile user_id='%s': %s", user_id, e)
        raise SupabaseRepositoryError(f"Database query failed for student profile '{user_id}': {e}") from e


def list_student_profiles() -> list[dict[str, Any]]:
    """List all student profiles directly from Supabase.

    Raises SupabaseRepositoryError on database failure.
    """
    try:
        client = get_client()
        res = client.table("student_profiles").select("*").execute()
        return res.data or []
    except Exception as e:
        logger.error("[SupabaseRepo] Failed listing student_profiles: %s", e)
        raise SupabaseRepositoryError(f"Database query failed for student profiles: {e}") from e


def upsert_student_profile(profile_data: dict[str, Any]) -> dict[str, Any]:
    """Authoritatively create or update a student profile in Supabase.

    Returns persisted profile record on success.
    Raises SupabaseRepositoryError on database failure.
    Does NOT write to local JSON.
    Does NOT treat in-memory _cache as authoritative.
    """
    try:
        client = get_client()
        res = client.table("student_profiles").upsert(profile_data).execute()
        saved = res.data[0] if (res.data and len(res.data) > 0) else profile_data
        logger.info("[SupabaseRepo] Confirmed Supabase upsert for student_profile '%s'", profile_data.get("user_id"))
        return saved
    except Exception as e:
        logger.error("[SupabaseRepo] Failed upserting student_profile user_id='%s': %s", profile_data.get("user_id"), e)
        raise SupabaseRepositoryError(f"Database upsert failed for student profile: {e}") from e


# ===========================================================================
# STUDENT ASSESSMENTS
# ===========================================================================

def get_student_assessment(assessment_id: str) -> dict[str, Any] | None:
    """Retrieve student assessment record directly from Supabase by id.

    Returns None if assessment not found.
    Raises SupabaseRepositoryError on database failure.
    """
    try:
        client = get_client()
        res = client.table("student_assessments").select("*").eq("id", assessment_id).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except Exception as e:
        logger.error("[SupabaseRepo] Failed fetching student_assessment id='%s': %s", assessment_id, e)
        raise SupabaseRepositoryError(f"Database query failed for student assessment '{assessment_id}': {e}") from e


def get_student_assessment_by_user(user_id: str, user_email: str | None = None) -> dict[str, Any] | None:
    """Retrieve student assessment record by user_id, assessment id, or email.

    Prioritizes latest user-submitted assessments over demo baselines.
    Returns None if not found.
    Raises SupabaseRepositoryError on database failure.
    """
    try:
        client = get_client()
        candidates = []
        # Query by user_id
        res_uid = client.table("student_assessments").select("*").eq("user_id", user_id).execute()
        if res_uid.data:
            candidates.extend(res_uid.data)
        # Query by id
        res_id = client.table("student_assessments").select("*").eq("id", user_id).execute()
        if res_id.data:
            candidates.extend(res_id.data)
        # Query by email if provided
        if user_email:
            res_email = client.table("student_assessments").select("*").eq("user_email", user_email).execute()
            if res_email.data:
                candidates.extend(res_email.data)

        if not candidates:
            return None

        # Deduplicate candidates by id preserving order
        unique_candidates = []
        seen_ids = set()
        for c in candidates:
            cid = c.get("id")
            if cid and cid not in seen_ids:
                seen_ids.add(cid)
                unique_candidates.append(c)

        # Sort so that latest USER_SUBMITTED assessment comes first
        return sorted(
            unique_candidates,
            key=lambda r: (
                1 if r.get("source") == "USER_SUBMITTED" or not r.get("is_demo", False) else 0,
                r.get("updated_at") or r.get("created_at") or "",
            ),
            reverse=True,
        )[0]
    except Exception as e:
        logger.error("[SupabaseRepo] Failed fetching student_assessment for user='%s': %s", user_id, e)
        raise SupabaseRepositoryError(f"Database query failed for student user '{user_id}': {e}") from e


def list_student_assessments(
    source: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """List student assessments directly from Supabase.

    Supports optional filtering by source ('USER_SUBMITTED', 'DEMO_SYNTHETIC', etc.).
    Raises SupabaseRepositoryError on database failure.
    """
    try:
        client = get_client()
        query = client.table("student_assessments").select("*")
        if source and source.lower() != "all":
            query = query.eq("source", source)
        res = query.execute()
        rows = res.data or []
        if limit is not None and limit > 0:
            rows = rows[:limit]
        return rows
    except Exception as e:
        logger.error("[SupabaseRepo] Failed listing student_assessments: %s", e)
        raise SupabaseRepositoryError(f"Database query failed for student assessments: {e}") from e


def create_student_assessment(assessment_data: dict[str, Any]) -> dict[str, Any]:
    """Authoritatively persist a student assessment record to Supabase.

    Returns inserted/upserted assessment record on success.
    Raises SupabaseRepositoryError on database failure.
    Does NOT write to local JSON.
    Does NOT treat in-memory _cache as authoritative.
    """
    try:
        client = get_client()
        res = client.table("student_assessments").upsert(assessment_data).execute()
        if not res.data or len(res.data) == 0:
            saved_row = assessment_data
        else:
            saved_row = res.data[0]
        logger.info("[SupabaseRepo] Confirmed Supabase persistence for student_assessment '%s'", assessment_data.get("id"))
        return saved_row
    except Exception as e:
        logger.error("[SupabaseRepo] Failed persisting student_assessment id='%s': %s", assessment_data.get("id"), e)
        raise SupabaseRepositoryError(f"Database persistence failed for student assessment: {e}") from e


def update_student_assessment(assessment_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    """Authoritatively update an existing student assessment record in Supabase.

    Returns updated assessment record on success.
    Raises AssessmentNotFoundError if no matching row was updated.
    Raises SupabaseRepositoryError on database failure.
    Does NOT write to local JSON.
    Does NOT treat in-memory _cache as authoritative.
    """
    try:
        client = get_client()
        res = client.table("student_assessments").update(updates).eq("id", assessment_id).execute()
        if not res.data or len(res.data) == 0:
            raise AssessmentNotFoundError(f"Student assessment record '{assessment_id}' not found in Supabase.")
        updated_row = res.data[0]
        logger.info("[SupabaseRepo] Confirmed Supabase update for student_assessment '%s'", assessment_id)
        return updated_row
    except SupabaseRepositoryError:
        raise
    except Exception as e:
        logger.error("[SupabaseRepo] Failed updating student_assessment id='%s': %s", assessment_id, e)
        raise SupabaseRepositoryError(f"Database update failed for student assessment '{assessment_id}': {e}") from e


def delete_student_assessment_repo(assessment_id: str) -> bool:
    """Authoritatively delete a student assessment record from Supabase."""
    try:
        client = get_client()
        res = client.table("student_assessments").delete().eq("id", assessment_id).execute()
        deleted = bool(getattr(res, "data", []))
        if deleted:
            logger.info("[SupabaseRepo] Confirmed Supabase deletion for student_assessment '%s'", assessment_id)
        return deleted
    except SupabaseRepositoryError:
        raise
    except Exception as e:
        logger.error("[SupabaseRepo] Failed deleting student_assessment id='%s': %s", assessment_id, e)
        raise SupabaseRepositoryError(f"Database deletion failed for student assessment '{assessment_id}': {e}") from e
