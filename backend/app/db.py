"""Database and data loader — supports Supabase PostgreSQL with robust fallback to demo dataset."""
import json
import logging
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger("skillsetu.db")

_cache: dict[str, list] = {}
_supabase_connected: bool = False


def _find_data_dir() -> Path:
    """Find the data/demo directory across various deployment topologies (local, Docker, Render)."""
    current_file = Path(__file__).resolve()
    candidates = [
        current_file.parent.parent.parent / "data" / "demo",  # Local repo root (backend/app/db.py -> root/data/demo)
        current_file.parent.parent / "data" / "demo",         # Docker /app/app/db.py -> /app/data/demo
        Path.cwd() / "data" / "demo",                         # Working directory is repo root
        Path.cwd().parent / "data" / "demo",                  # Working directory is backend/
        Path("/app/data/demo"),                               # Docker container standard
        Path("/data/demo"),                                   # Container root fallback
    ]
    for c in candidates:
        try:
            if c.is_dir() and any(c.glob("*.json")):
                return c
        except Exception:
            continue
    return candidates[0]


def get_supabase_client():
    """Return Supabase client if configured on Render/backend, else None."""
    global _supabase_connected
    if not settings.supabase_url:
        _supabase_connected = False
        return None
    key = settings.supabase_service_key or settings.supabase_anon_key
    if not key:
        _supabase_connected = False
        return None
    try:
        from supabase import create_client
        client = create_client(settings.supabase_url, key)
        _supabase_connected = True
        return client
    except Exception as e:
        logger.warning("[DB] Could not initialize Supabase client: %s", e)
        _supabase_connected = False
        return None


def is_supabase_connected() -> bool:
    """Check if Supabase client is connected."""
    return _supabase_connected


def load_demo_data() -> int:
    """Load all demo JSON files into memory cache."""
    data_dir = _find_data_dir()
    loaded_count = 0
    if not data_dir.is_dir():
        logger.error("[DB] Data directory not found. Checked candidate paths.")
        return 0

    for f in data_dir.glob("*.json"):
        try:
            records = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(records, list):
                _cache[f.stem] = records
                loaded_count += len(records)
            elif isinstance(records, dict):
                _cache[f.stem] = [records]
                loaded_count += 1
        except Exception as e:
            logger.warning("[DB] Failed loading demo file %s: %s", f.name, e)

    logger.info("[DB] Loaded %d records across %d tables from %s", loaded_count, len(_cache), data_dir)
    return loaded_count


def init_db():
    """Initialize data layer: load baseline dataset, overlay Supabase data if connected."""
    # 1. Always load baseline dataset first so system is never empty
    demo_count = load_demo_data()

    # 2. If Supabase is configured, overlay table data
    client = get_supabase_client()
    if client:
        logger.info("[DB] Supabase configured at %s. Syncing tables...", settings.supabase_url)
        tables = [
            "skills", "jobs", "job_skills", "courses", "course_skills",
            "placements", "employers", "employer_feedback", "industry_signals",
            "skill_forecasts", "student_profiles", "schemes", "sync_logs",
            "employer_demands", "difficult_skills", "student_assessments",
            "gov_opportunities", "users"
        ]
        for tbl in tables:
            try:
                res = client.table(tbl).select("*").execute()
                if res.data and len(res.data) > 0:
                    _cache[tbl] = res.data
                    logger.info("[DB] Loaded %d records from Supabase table '%s'", len(res.data), tbl)
            except Exception as e:
                logger.warning("[DB] Supabase table '%s' query error: %s", tbl, e)

    # 3. Ensure baseline demo users exist for local testing and demonstration
    init_demo_users()


def get_demo(table: str) -> list[dict]:
    """Get data for a table name. Returns empty list if not found."""
    if not _cache:
        load_demo_data()
    return _cache.get(table, [])


def set_demo(table: str, data: list[dict]):
    """Set data for a table name."""
    _cache[table] = data


def append_demo(table: str, record: dict):
    """Append a single record to the cached table."""
    if table not in _cache:
        _cache[table] = []
    _cache[table].append(record)


def save_employer_feedback(
    feedback_id: str,
    status: str,
    notes: str | None = None,
    proficiency_required: str | None = None,
) -> dict | None:
    """Update employer feedback in-memory cache and write through to Supabase if connected."""
    if not _cache:
        load_demo_data()
    matched_record = None
    feedback_list = _cache.get("employer_feedback", [])
    for f in feedback_list:
        if f.get("id") == feedback_id:
            f["status"] = status
            if notes is not None:
                f["notes"] = notes
            if proficiency_required is not None:
                f["proficiency_required"] = proficiency_required
            matched_record = f
            break

    # Write-through to Supabase
    client = get_supabase_client()
    if client:
        try:
            payload: dict[str, Any] = {"status": status}
            if notes is not None:
                payload["notes"] = notes
            if proficiency_required is not None:
                payload["proficiency_required"] = proficiency_required

            client.table("employer_feedback").update(payload).eq("id", feedback_id).execute()
            logger.info("[DB] Persisted employer feedback '%s' (%s) to Supabase.", feedback_id, status)
        except Exception as e:
            logger.warning("[DB] Failed persisting employer feedback to Supabase: %s", e)

    return matched_record


def save_employer_demand(demand_data: dict) -> dict:
    """Save new employer-submitted skill demand requirement to cache and Supabase if connected."""
    if not _cache:
        load_demo_data()
    demands = _cache.setdefault("employer_demands", [])
    demands.insert(0, demand_data)

    client = get_supabase_client()
    if client:
        try:
            client.table("employer_demands").upsert(demand_data).execute()
            logger.info("[DB] Persisted employer demand '%s' to Supabase.", demand_data.get("id"))
        except Exception as e:
            logger.warning("[DB] Failed persisting employer demand to Supabase: %s", e)

    return demand_data


def update_employer_demand_status(
    demand_id: str,
    new_status: str,
    admin_notes: str | None = None,
    validated_by: str | None = None,
) -> dict | None:
    """Update validation status of an employer demand record."""
    if not _cache:
        load_demo_data()
    demands = _cache.get("employer_demands", [])
    matched = None
    for d in demands:
        if d.get("id") == demand_id:
            d["validation_status"] = new_status
            if admin_notes is not None:
                d["admin_notes"] = admin_notes
            if validated_by is not None:
                d["validated_by"] = validated_by
            matched = d
            break

    if matched:
        client = get_supabase_client()
        if client:
            try:
                payload: dict[str, Any] = {"validation_status": new_status}
                if admin_notes is not None:
                    payload["admin_notes"] = admin_notes
                if validated_by is not None:
                    payload["validated_by"] = validated_by
                client.table("employer_demands").update(payload).eq("id", demand_id).execute()
                logger.info("[DB] Updated employer demand '%s' status to %s in Supabase.", demand_id, new_status)
            except Exception as e:
                logger.warning("[DB] Failed updating employer demand in Supabase: %s", e)

    return matched


def delete_employer_demand(demand_id: str) -> bool:
    """Delete employer demand record from in-memory cache and Supabase."""
    if not _cache:
        load_demo_data()
    demands = _cache.get("employer_demands", [])
    initial_len = len(demands)
    _cache["employer_demands"] = [d for d in demands if d.get("id") != demand_id]
    deleted = len(_cache["employer_demands"]) < initial_len

    if deleted:
        client = get_supabase_client()
        if client:
            try:
                client.table("employer_demands").delete().eq("id", demand_id).execute()
                logger.info("[DB] Deleted employer demand '%s' from Supabase.", demand_id)
            except Exception as e:
                logger.warning("[DB] Failed deleting employer demand from Supabase: %s", e)

    return deleted




def save_sync_log(log_entry: dict) -> bool:
    """Save or update sync audit log in memory and Supabase."""
    if not _cache:
        load_demo_data()
    sync_id = log_entry.get("id")
    logs = _cache.setdefault("sync_logs", [])
    updated = False
    for idx, item in enumerate(logs):
        if item.get("id") == sync_id:
            logs[idx] = log_entry
            updated = True
            break
    if not updated:
        logs.append(log_entry)

    client = get_supabase_client()
    if client:
        try:
            client.table("sync_logs").upsert(log_entry).execute()
            logger.info("[DB] Persisted sync_log '%s' (%s) to Supabase.", sync_id, log_entry.get("status"))
            return True
        except Exception as e:
            logger.warning("[DB] Failed persisting sync_log to Supabase: %s", e)
    return False


def persist_schemes_to_supabase(schemes: list[dict]):
    """Write transformed schemes to Supabase if connected."""
    client = get_supabase_client()
    if not client or not schemes:
        return
    for s in schemes:
        try:
            client.table("schemes").upsert(s, on_conflict="source,external_id").execute()
        except Exception as e:
            logger.warning("[DB] Failed persisting scheme '%s' to Supabase: %s", s.get("id"), e)


def persist_jobs_to_supabase(jobs: list[dict]):
    """Write transformed opportunities/jobs to Supabase if connected."""
    client = get_supabase_client()
    if not client or not jobs:
        return
    for j in jobs:
        try:
            client.table("jobs").upsert(j, on_conflict="source,external_id").execute()
        except Exception as e:
            logger.warning("[DB] Failed persisting job/opp '%s' to Supabase: %s", j.get("id"), e)


def save_student_assessment(assessment_data: dict) -> dict:
    """Save new student-submitted self-assessment record to memory cache and write-through to Supabase if connected."""
    if not _cache:
        load_demo_data()
    assessments = _cache.setdefault("student_assessments", [])
    assessments.insert(0, assessment_data)

    client = get_supabase_client()
    if client:
        try:
            client.table("student_assessments").upsert(assessment_data).execute()
            logger.info("[DB] Persisted student assessment '%s' to Supabase.", assessment_data.get("id"))
        except Exception as e:
            logger.warning("[DB] Failed persisting student assessment to Supabase: %s", e)

    return assessment_data


def delete_student_assessment(assessment_id: str) -> bool:
    """Delete student assessment from in-memory cache and Supabase if connected."""
    if not _cache:
        load_demo_data()
    assessments = _cache.get("student_assessments", [])
    initial_len = len(assessments)
    _cache["student_assessments"] = [a for a in assessments if a.get("id") != assessment_id]
    deleted = len(_cache["student_assessments"]) < initial_len

    if deleted:
        client = get_supabase_client()
        if client:
            try:
                client.table("student_assessments").delete().eq("id", assessment_id).execute()
                logger.info("[DB] Deleted student assessment '%s' from Supabase.", assessment_id)
            except Exception as e:
                logger.warning("[DB] Failed deleting student assessment from Supabase: %s", e)

    return deleted


def save_course(course_data: dict) -> dict:
    """Save new course or institute training program to cache and Supabase if connected."""
    if not _cache:
        load_demo_data()
    courses = _cache.setdefault("courses", [])
    courses.insert(0, course_data)

    client = get_supabase_client()
    if client:
        try:
            client.table("courses").upsert(course_data).execute()
            logger.info("[DB] Persisted course '%s' to Supabase.", course_data.get("id"))
        except Exception as e:
            logger.warning("[DB] Failed persisting course to Supabase: %s", e)

    return course_data


def update_course(course_id: str, updates: dict) -> dict | None:
    """Update fields on a course record."""
    if not _cache:
        load_demo_data()
    courses = _cache.get("courses", [])
    matched = None
    for c in courses:
        if c.get("id") == course_id:
            c.update(updates)
            matched = c
            break

    if matched:
        client = get_supabase_client()
        if client:
            try:
                client.table("courses").update(updates).eq("id", course_id).execute()
                logger.info("[DB] Updated course '%s' in Supabase.", course_id)
            except Exception as e:
                logger.warning("[DB] Failed updating course in Supabase: %s", e)

    return matched


def delete_course(course_id: str) -> bool:
    """Delete course record from cache and Supabase."""
    if not _cache:
        load_demo_data()
    courses = _cache.get("courses", [])
    initial_len = len(courses)
    _cache["courses"] = [c for c in courses if c.get("id") != course_id]
    deleted = len(_cache["courses"]) < initial_len

    if deleted:
        client = get_supabase_client()
        if client:
            try:
                client.table("courses").delete().eq("id", course_id).execute()
                logger.info("[DB] Deleted course '%s' from Supabase.", course_id)
            except Exception as e:
                logger.warning("[DB] Failed deleting course from Supabase: %s", e)

    return deleted


def save_gov_opportunity(data: dict) -> dict:
    """Save new government opportunity record to cache and Supabase if connected."""
    if not _cache:
        load_demo_data()
    records = _cache.setdefault("gov_opportunities", [])
    records.insert(0, data)

    client = get_supabase_client()
    if client:
        try:
            client.table("gov_opportunities").upsert(data).execute()
            logger.info("[DB] Persisted gov opportunity '%s' to Supabase.", data.get("id"))
        except Exception as e:
            logger.warning("[DB] Failed persisting gov opportunity to Supabase: %s", e)

    return data


def update_gov_opportunity(opp_id: str, updates: dict) -> dict | None:
    """Update fields on a government opportunity record."""
    if not _cache:
        load_demo_data()
    records = _cache.get("gov_opportunities", [])
    matched = None
    for r in records:
        if r.get("id") == opp_id:
            r.update(updates)
            matched = r
            break

    if matched:
        client = get_supabase_client()
        if client:
            try:
                client.table("gov_opportunities").update(updates).eq("id", opp_id).execute()
                logger.info("[DB] Updated gov opportunity '%s' in Supabase.", opp_id)
            except Exception as e:
                logger.warning("[DB] Failed updating gov opportunity in Supabase: %s", e)

    return matched


def delete_gov_opportunity(opp_id: str) -> bool:
    """Delete government opportunity record from cache and Supabase."""
    if not _cache:
        load_demo_data()
    records = _cache.get("gov_opportunities", [])
    initial_len = len(records)
    _cache["gov_opportunities"] = [r for r in records if r.get("id") != opp_id]
    deleted = len(_cache["gov_opportunities"]) < initial_len

    if deleted:
        client = get_supabase_client()
        if client:
            try:
                client.table("gov_opportunities").delete().eq("id", opp_id).execute()
                logger.info("[DB] Deleted gov opportunity '%s' from Supabase.", opp_id)
            except Exception as e:
                logger.warning("[DB] Failed deleting gov opportunity from Supabase: %s", e)

    return deleted


# ---------------------------------------------------------------------------
# Phase 23: User Identity & Authentication Persistence
# ---------------------------------------------------------------------------

def init_demo_users():
    """Ensure baseline demo accounts exist for each role with bcrypt hashed passwords."""
    if not _cache:
        load_demo_data()
    users = _cache.setdefault("users", [])
    if users:
        return

    from app.core.security import hash_password

    demo_accounts = [
        {
            "id": "usr-student-001",
            "email": "student@skillsetu.gov.in",
            "hashed_password": hash_password("Password@123"),
            "full_name": "Aarav Patil",
            "role": "STUDENT",
            "organization_id": None,
            "district": "Pune",
            "is_active": True,
            "created_at": "2026-01-15T09:00:00Z",
            "updated_at": "2026-01-15T09:00:00Z",
        },
        {
            "id": "usr-employer-001",
            "email": "employer@skillsetu.gov.in",
            "hashed_password": hash_password("Password@123"),
            "full_name": "Tata Motors Skill Lead",
            "role": "EMPLOYER",
            "organization_id": "emp-001",
            "district": "Pune",
            "is_active": True,
            "created_at": "2026-01-15T09:00:00Z",
            "updated_at": "2026-01-15T09:00:00Z",
        },
        {
            "id": "usr-employer-002",
            "email": "employer2@skillsetu.gov.in",
            "hashed_password": hash_password("Password@123"),
            "full_name": "Bajaj Auto Talent Head",
            "role": "EMPLOYER",
            "organization_id": "emp-002",
            "district": "Pune",
            "is_active": True,
            "created_at": "2026-01-15T09:00:00Z",
            "updated_at": "2026-01-15T09:00:00Z",
        },
        {
            "id": "usr-institute-001",
            "email": "institute@skillsetu.gov.in",
            "hashed_password": hash_password("Password@123"),
            "full_name": "COEP Vocational Director",
            "role": "INSTITUTE",
            "organization_id": "inst-coep",
            "district": "Pune",
            "is_active": True,
            "created_at": "2026-01-15T09:00:00Z",
            "updated_at": "2026-01-15T09:00:00Z",
        },
        {
            "id": "usr-institute-002",
            "email": "institute2@skillsetu.gov.in",
            "hashed_password": hash_password("Password@123"),
            "full_name": "VJTI Principal",
            "role": "INSTITUTE",
            "organization_id": "inst-vjti",
            "district": "Mumbai City",
            "is_active": True,
            "created_at": "2026-01-15T09:00:00Z",
            "updated_at": "2026-01-15T09:00:00Z",
        },
        {
            "id": "usr-gov-001",
            "email": "government@skillsetu.gov.in",
            "hashed_password": hash_password("Password@123"),
            "full_name": "Maharashtra Skill Officer",
            "role": "GOVERNMENT",
            "organization_id": "gov-msis",
            "district": "Mumbai City",
            "is_active": True,
            "created_at": "2026-01-15T09:00:00Z",
            "updated_at": "2026-01-15T09:00:00Z",
        },
        {
            "id": "usr-admin-001",
            "email": "admin@skillsetu.gov.in",
            "hashed_password": hash_password("AdminPass@2026"),
            "full_name": "SkillSetu System Administrator",
            "role": "ADMIN",
            "organization_id": "admin-gov",
            "district": "Maharashtra",
            "is_active": True,
            "created_at": "2026-01-15T09:00:00Z",
            "updated_at": "2026-01-15T09:00:00Z",
        },
    ]
    users.extend(demo_accounts)


def get_user_by_email(email: str) -> dict | None:
    """Find user record by case-insensitive email address."""
    if not _cache:
        load_demo_data()
    users = _cache.get("users", [])
    clean_email = email.strip().lower()
    for u in users:
        if u.get("email", "").strip().lower() == clean_email:
            return u
    return None


def get_user_by_id(user_id: str) -> dict | None:
    """Find user record by ID."""
    if not _cache:
        load_demo_data()
    users = _cache.get("users", [])
    for u in users:
        if u.get("id") == user_id:
            return u
    return None


def list_users() -> list[dict]:
    """Return all user accounts."""
    if not _cache:
        load_demo_data()
    return _cache.get("users", [])


def save_user(user_data: dict) -> dict:
    """Save or update user record in memory cache and Supabase write-through."""
    if not _cache:
        load_demo_data()
    users = _cache.setdefault("users", [])
    existing_idx = next((i for i, u in enumerate(users) if u.get("id") == user_data.get("id") or u.get("email", "").lower() == user_data.get("email", "").lower()), None)
    if existing_idx is not None:
        users[existing_idx] = user_data
    else:
        users.append(user_data)

    client = get_supabase_client()
    if client:
        try:
            client.table("users").upsert(user_data).execute()
            logger.info("[DB] Persisted user '%s' (%s) to Supabase.", user_data.get("email"), user_data.get("role"))
        except Exception as e:
            logger.warning("[DB] Failed persisting user to Supabase: %s", e)

    return user_data



