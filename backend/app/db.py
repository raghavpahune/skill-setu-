from datetime import datetime, timezone
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


def _find_real_data_dir() -> Path:
    """Find or create the data/real directory for persistent first-party user submissions."""
    demo_dir = _find_data_dir()
    real_dir = demo_dir.parent / "real"
    try:
        real_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return real_dir


def _flush_real_table(table: str):
    """Write all user-submitted and real ingested records for a table to data/real/{table}.json."""
    try:
        real_dir = _find_real_data_dir()
        records = _cache.get(table, [])
        real_records = [
            r for r in records
            if isinstance(r, dict) and (
                r.get("source") in ("USER_SUBMITTED", "EMPLOYER_SUBMITTED", "INSTITUTE_SUBMITTED", "REAL_INGESTED", "LIVE_API")
                or (r.get("is_demo") is False and r.get("source") != "DEMO_SYNTHETIC")
            )
        ]

        # ponytail: runtime users persist to users_runtime.json (not users.json)
        # so load_real_data can skip the fixture file while still loading persisted users
        filename = "users_runtime" if table == "users" else table
        out_file = real_dir / f"{filename}.json"
        out_file.write_text(json.dumps(real_records, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("[DB] Flushed %d real records to %s", len(real_records), out_file)
    except Exception as e:
        logger.warning("[DB] Failed flushing real table '%s' to disk: %s", table, e)


def get_supabase_client():
    """Return Supabase client if configured on Render/backend, else None."""
    global _supabase_connected
    try:
        from app.repositories.supabase_repository import _client_override
        if _client_override is not None:
            _supabase_connected = True
            return _client_override
    except Exception:
        pass
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
    """Load all demo JSON files into memory cache, normalizing DEMO_SYNTHETIC provenance."""
    data_dir = _find_data_dir()
    loaded_count = 0
    if not data_dir.is_dir():
        logger.error("[DB] Data directory not found. Checked candidate paths.")
        return 0

    for f in data_dir.glob("*.json"):
        try:
            records = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(records, list):
                for r in records:
                    if isinstance(r, dict):
                        if "source" not in r:
                            r["source"] = "DEMO_SYNTHETIC"
                        if "is_demo" not in r:
                            r["is_demo"] = True
                _cache[f.stem] = records
                loaded_count += len(records)
            elif isinstance(records, dict):
                if "source" not in records:
                    records["source"] = "DEMO_SYNTHETIC"
                if "is_demo" not in records:
                    records["is_demo"] = True
                _cache[f.stem] = [records]
                loaded_count += 1
        except Exception as e:
            logger.warning("[DB] Failed loading demo file %s: %s", f.name, e)

    logger.info("[DB] Loaded %d baseline demo records across %d tables from %s", loaded_count, len(_cache), data_dir)
    return loaded_count


def load_real_data() -> int:
    """Load and overlay real user-submitted records from data/real directory into _cache."""
    real_dir = _find_real_data_dir()
    loaded_count = 0
    if not real_dir.is_dir():
        return 0

    for f in real_dir.glob("*.json"):
        if f.name == "README.md":
            continue
        # SECURITY: skip users.json fixture file — test fixture accounts must not become
        # valid production login identities. Runtime-persisted users live in
        # users_runtime.json (written by save_user/_flush_real_table) and load normally.
        if f.name == "users.json":
            continue
        try:
            records = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(records, list) and len(records) > 0:
                table = f.stem
                if table == "users_runtime":
                    table = "users"
                existing = _cache.setdefault(table, [])
                existing_ids = {r.get("id") for r in existing if isinstance(r, dict) and r.get("id")}
                # Prepend / merge real records
                for r in records:
                    if not isinstance(r, dict):
                        continue
                    r["source"] = r.get("source") or "USER_SUBMITTED"
                    r["is_demo"] = False
                    rid = r.get("id")
                    if rid and rid in existing_ids:
                        for idx, item in enumerate(existing):
                            if isinstance(item, dict) and item.get("id") == rid:
                                existing[idx] = r
                                break
                    else:
                        existing.insert(0, r)
                loaded_count += len(records)
        except Exception as e:
            logger.warning("[DB] Failed loading real data file %s: %s", f.name, e)

    if loaded_count > 0:
        logger.info("[DB] Loaded %d real user records across tables from %s", loaded_count, real_dir)
    return loaded_count


def init_db():
    """Initialize hybrid data layer: load synthetic baseline, overlay real submissions, then Supabase if configured."""
    # 1. Always load baseline synthetic dataset first so system is never empty
    demo_count = load_demo_data()

    # 2. Overlay persistent first-party user submissions from disk
    real_count = load_real_data()

    # 3. If Supabase is configured, overlay table data
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
                    existing = _cache.setdefault(tbl, [])
                    existing_ids = {r.get("id") for r in existing if isinstance(r, dict) and r.get("id")}
                    for r in res.data:
                        if not isinstance(r, dict):
                            continue
                        rid = r.get("id")
                        if rid and rid in existing_ids:
                            for idx, item in enumerate(existing):
                                if isinstance(item, dict) and item.get("id") == rid:
                                    existing[idx] = r
                                    break
                        else:
                            existing.insert(0, r)
                    logger.info("[DB] Merged %d records from Supabase table '%s'", len(res.data), tbl)
            except Exception as e:
                logger.warning("[DB] Supabase table '%s' query error: %s", tbl, e)

    # 4. Ensure baseline demo users exist for local testing and demonstration
    init_demo_users()


def get_data_governance_summary() -> dict[str, Any]:
    """Return data governance breakdown of real user submissions vs synthetic demo baseline."""
    if not _cache:
        init_db()

    tables = [
        "student_assessments", "student_profiles", "employer_demands",
        "employer_feedback", "courses", "industry_signals",
        "gov_opportunities", "users", "jobs", "skills"
    ]
    summary = {}
    total_real = 0
    total_demo = 0

    # For migrated authoritative domains, fetch directly from Supabase repositories if available
    for tbl in tables:
        records: list[dict[str, Any]] = []
        try:
            if tbl == "student_assessments":
                from app.repositories.supabase_repository import list_student_assessments
                records = list_student_assessments()
            elif tbl == "student_profiles":
                from app.repositories.supabase_repository import list_student_profiles
                records = list_student_profiles()
            elif tbl == "employer_demands":
                from app.repositories.supabase_repository import list_employer_demands
                records = list_employer_demands()
            elif tbl == "employer_feedback":
                from app.repositories.supabase_repository import list_employer_feedback
                records = list_employer_feedback()
            elif tbl == "courses":
                from app.repositories.supabase_repository import list_courses
                records = list_courses()
            elif tbl == "industry_signals":
                from app.repositories.supabase_repository import list_industry_signals as list_signals_repo
                records = list_signals_repo()
            else:
                records = _cache.get(tbl, [])
        except Exception:
            records = _cache.get(tbl, [])

        real_count = sum(
            1 for r in records
            if isinstance(r, dict) and (
                r.get("source") in ("USER_SUBMITTED", "EMPLOYER_SUBMITTED", "INSTITUTE_SUBMITTED", "REAL_INGESTED", "LIVE_API")
                or (r.get("is_demo") is False and r.get("source") != "DEMO_SYNTHETIC")
            )
        )
        demo_count = len(records) - real_count

        total_real += real_count
        total_demo += demo_count
        summary[tbl] = {
            "total": len(records),
            "real_user_submitted": real_count,
            "demo_synthetic": demo_count,
            "has_live_data": real_count > 0,
        }

    return {
        "status": "success",
        "total_records": total_real + total_demo,
        "total_real_user_submitted": total_real,
        "total_demo_synthetic": total_demo,
        "live_data_active": total_real > 0,
        "tables": summary,
    }




def get_demo(table: str) -> list[dict]:
    """Get data for a table name. Returns empty list if not found."""
    if not _cache:
        init_db()
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
    user_id: str | None = None,
    user_email: str | None = None,
) -> dict | None:
    """Update employer feedback in-memory cache, flush to real storage, and write through to Supabase if connected."""
    if not _cache:
        init_db()
    matched_record = None
    feedback_list = _cache.get("employer_feedback", [])
    now_iso = datetime.now(timezone.utc).isoformat()
    for f in feedback_list:
        if f.get("id") == feedback_id:
            f["status"] = status
            f["source"] = "USER_SUBMITTED"
            f["is_demo"] = False
            f["updated_at"] = now_iso
            if notes is not None:
                f["notes"] = notes
            if proficiency_required is not None:
                f["proficiency_required"] = proficiency_required
            if user_id is not None:
                f["user_id"] = user_id
            if user_email is not None:
                f["user_email"] = user_email
            matched_record = f
            break

    if matched_record:
        _flush_real_table("employer_feedback")

    # Write-through to Supabase
    client = get_supabase_client()
    if client:
        try:
            payload: dict[str, Any] = {"status": status, "updated_at": now_iso}
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
    """Save new employer-submitted skill demand requirement to cache, disk storage, and Supabase."""
    if not _cache:
        init_db()
    now_iso = datetime.now(timezone.utc).isoformat()
    demand_data.setdefault("created_at", now_iso)
    demand_data["updated_at"] = now_iso
    demand_data.setdefault("source", "USER_SUBMITTED")
    demand_data["is_demo"] = False
    demands = _cache.setdefault("employer_demands", [])
    did = demand_data.get("id")
    existing_idx = next((i for i, d in enumerate(demands) if did and d.get("id") == did), None)
    if existing_idx is not None:
        demands[existing_idx] = demand_data
    else:
        demands.insert(0, demand_data)
    _flush_real_table("employer_demands")

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
    """Update validation status of an employer demand record and flush to disk."""
    payload: dict[str, Any] = {
        "validation_status": new_status,
        "status": new_status.lower(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if admin_notes is not None:
        payload["admin_notes"] = admin_notes
    if validated_by is not None:
        payload["validated_by"] = validated_by

    matched = None
    try:
        from app.repositories.supabase_repository import update_employer_demand, DemandNotFoundError
        matched = update_employer_demand(demand_id, payload)
    except DemandNotFoundError:
        matched = None
    except Exception as e:
        logger.error("[DB] Supabase update failed for employer_demand '%s': %s", demand_id, e)
        raise

    if not _cache:
        init_db()
    demands = _cache.get("employer_demands", [])
    cache_matched = False
    for d in demands:
        if d.get("id") == demand_id:
            d.update(payload)
            matched = d
            cache_matched = True
            break

    if cache_matched:
        _flush_real_table("employer_demands")
    elif matched is not None and "employer_demands" in _cache:
        _cache["employer_demands"].insert(0, matched)

    return matched


def delete_employer_demand(demand_id: str) -> bool:
    """Delete employer demand record from in-memory cache, disk storage, and Supabase."""
    repo_deleted = False
    try:
        from app.repositories.supabase_repository import delete_employer_demand_repo
        repo_deleted = delete_employer_demand_repo(demand_id)
    except Exception as e:
        logger.error("[DB] Supabase delete failed for employer_demand '%s': %s", demand_id, e)
        raise

    if not _cache:
        init_db()
    demands = _cache.get("employer_demands", [])
    initial_len = len(demands)
    _cache["employer_demands"] = [d for d in demands if d.get("id") != demand_id]
    cache_deleted = len(_cache["employer_demands"]) < initial_len

    if cache_deleted:
        _flush_real_table("employer_demands")

    return repo_deleted or cache_deleted


def save_sync_log(log_entry: dict) -> bool:
    """Save or update sync audit log in memory and Supabase."""
    if not _cache:
        init_db()
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
    """Save new student-submitted self-assessment record to Supabase repository and sync cache/disk."""
    now_iso = datetime.now(timezone.utc).isoformat()
    assessment_data.setdefault("created_at", now_iso)
    assessment_data["updated_at"] = now_iso
    assessment_data.setdefault("source", "USER_SUBMITTED")
    assessment_data["is_demo"] = False

    from app.repositories.supabase_repository import create_student_assessment
    create_student_assessment(assessment_data)

    if not _cache:
        init_db()
    assessments = _cache.setdefault("student_assessments", [])
    
    # Check if this student already submitted, update or prepend
    aid = assessment_data.get("id")
    uid = assessment_data.get("user_id")
    existing_idx = next(
        (i for i, a in enumerate(assessments) if (aid and a.get("id") == aid) or (uid and a.get("user_id") == uid)),
        None
    )
    if existing_idx is not None:
        assessments[existing_idx] = assessment_data
    else:
        assessments.insert(0, assessment_data)

    _flush_real_table("student_assessments")

    return assessment_data


def delete_student_assessment(assessment_id: str) -> bool:
    """Delete student assessment from Supabase repository and sync cache/disk."""
    from app.repositories.supabase_repository import delete_student_assessment_repo
    repo_deleted = delete_student_assessment_repo(assessment_id)

    if not _cache:
        init_db()
    assessments = _cache.get("student_assessments", [])
    initial_len = len(assessments)
    _cache["student_assessments"] = [a for a in assessments if a.get("id") != assessment_id]
    deleted = len(_cache["student_assessments"]) < initial_len

    if deleted:
        _flush_real_table("student_assessments")

    return repo_deleted or deleted


def save_course(course_data: dict) -> dict:
    """Save new course or institute training program to Supabase repository and sync cache/disk."""
    now_iso = datetime.now(timezone.utc).isoformat()
    course_data.setdefault("created_at", now_iso)
    course_data["updated_at"] = now_iso
    course_data.setdefault("source", "USER_SUBMITTED")
    course_data["is_demo"] = False

    from app.repositories.supabase_repository import create_course
    create_course(course_data)

    if not _cache:
        init_db()
    courses = _cache.setdefault("courses", [])
    cid = course_data.get("id")
    existing_idx = next((i for i, c in enumerate(courses) if cid and c.get("id") == cid), None)
    if existing_idx is not None:
        courses[existing_idx] = course_data
    else:
        courses.insert(0, course_data)
    _flush_real_table("courses")

    return course_data


def update_course(course_id: str, updates: dict) -> dict | None:
    """Update fields on a course record in Supabase repository and sync cache/disk."""
    from app.repositories.supabase_repository import update_course_repo, CourseNotFoundError
    try:
        update_course_repo(course_id, updates)
    except CourseNotFoundError:
        pass
    except Exception as e:
        logger.error("[DB] Failed updating course in Supabase repository: %s", e)
        raise

    if not _cache:
        init_db()
    courses = _cache.get("courses", [])
    matched = None
    for c in courses:
        if c.get("id") == course_id:
            c.update(updates)
            c["updated_at"] = datetime.now(timezone.utc).isoformat()
            matched = c
            break

    if matched:
        _flush_real_table("courses")

    return matched


def delete_course(course_id: str) -> bool:
    """Delete course record from Supabase repository and sync cache/disk."""
    from app.repositories.supabase_repository import delete_course_repo
    try:
        repo_deleted = delete_course_repo(course_id)
    except Exception as e:
        logger.error("[DB] Failed deleting course in Supabase repository: %s", e)
        raise

    if not _cache:
        init_db()
    courses = _cache.get("courses", [])
    initial_len = len(courses)
    _cache["courses"] = [c for c in courses if c.get("id") != course_id]
    deleted = len(_cache["courses"]) < initial_len

    if deleted:
        _flush_real_table("courses")

    return repo_deleted or deleted


def save_gov_opportunity(data: dict) -> dict:
    """Save new government opportunity record to cache, disk storage, and Supabase."""
    if not _cache:
        init_db()
    now_iso = datetime.now(timezone.utc).isoformat()
    data.setdefault("created_at", now_iso)
    data["updated_at"] = now_iso
    data.setdefault("source", "USER_SUBMITTED")
    data["is_demo"] = False

    client = get_supabase_client()
    if client:
        try:
            client.table("gov_opportunities").upsert(data).execute()
            logger.info("[DB] Persisted gov opportunity '%s' to Supabase.", data.get("id"))
        except Exception as e:
            logger.error("[DB] Failed persisting gov opportunity to Supabase: %s", e)
            from app.repositories.supabase_repository import SupabaseRepositoryError
            raise SupabaseRepositoryError(f"Database insertion failed for gov opportunity: {e}") from e

    records = _cache.setdefault("gov_opportunities", [])
    gid = data.get("id")
    existing_idx = next((i for i, g in enumerate(records) if gid and g.get("id") == gid), None)
    if existing_idx is not None:
        records[existing_idx] = data
    else:
        records.insert(0, data)
    _flush_real_table("gov_opportunities")

    return data


def update_gov_opportunity(opp_id: str, updates: dict) -> dict | None:
    """Update fields on a government opportunity record and flush to disk."""
    client = get_supabase_client()
    if client:
        try:
            res = client.table("gov_opportunities").update(updates).eq("id", opp_id).execute()
            logger.info("[DB] Updated gov opportunity '%s' in Supabase.", opp_id)
        except Exception as e:
            logger.error("[DB] Failed updating gov opportunity in Supabase: %s", e)
            from app.repositories.supabase_repository import SupabaseRepositoryError
            raise SupabaseRepositoryError(f"Database update failed for gov opportunity: {e}") from e

    if not _cache:
        init_db()
    records = _cache.get("gov_opportunities", [])
    matched = None
    for r in records:
        if r.get("id") == opp_id:
            r.update(updates)
            r["updated_at"] = datetime.now(timezone.utc).isoformat()
            matched = r
            break

    if matched:
        _flush_real_table("gov_opportunities")

    return matched


def delete_gov_opportunity(opp_id: str) -> bool:
    """Delete government opportunity record from cache, disk storage, and Supabase."""
    client = get_supabase_client()
    if client:
        try:
            client.table("gov_opportunities").delete().eq("id", opp_id).execute()
            logger.info("[DB] Deleted gov opportunity '%s' from Supabase.", opp_id)
        except Exception as e:
            logger.error("[DB] Failed deleting gov opportunity from Supabase: %s", e)
            from app.repositories.supabase_repository import SupabaseRepositoryError
            raise SupabaseRepositoryError(f"Database deletion failed for gov opportunity: {e}") from e

    if not _cache:
        init_db()
    records = _cache.get("gov_opportunities", [])
    initial_len = len(records)
    _cache["gov_opportunities"] = [r for r in records if r.get("id") != opp_id]
    deleted = len(_cache["gov_opportunities"]) < initial_len

    if deleted:
        _flush_real_table("gov_opportunities")

    return deleted
# ---------------------------------------------------------------------------
# Phase 26: Industry Intelligence & Signals Persistence
# ---------------------------------------------------------------------------

def save_industry_signal(signal_data: dict) -> dict:
    """Save or insert industry intelligence signal authoritatively into Supabase."""
    from app.repositories.supabase_repository import create_industry_signal
    saved = create_industry_signal(signal_data)
    if "industry_signals" in _cache:
        signals = _cache["industry_signals"]
        idx = next((i for i, s in enumerate(signals) if s.get("id") == saved.get("id")), None)
        if idx is not None:
            signals[idx] = saved
        else:
            signals.insert(0, saved)
    return saved


def update_industry_signal(sig_id: str, updates: dict) -> dict | None:
    """Update fields on an industry intelligence signal record authoritatively in Supabase."""
    from app.repositories.supabase_repository import update_industry_signal_repo, IndustrySignalNotFoundError
    try:
        updated = update_industry_signal_repo(sig_id, updates)
        if "industry_signals" in _cache:
            for s in _cache["industry_signals"]:
                if s.get("id") == sig_id:
                    s.update(updated)
                    break
        return updated
    except IndustrySignalNotFoundError:
        return None


def delete_industry_signal(sig_id: str) -> bool:
    """Delete industry intelligence signal authoritatively from Supabase."""
    from app.repositories.supabase_repository import delete_industry_signal_repo
    deleted = delete_industry_signal_repo(sig_id)
    if "industry_signals" in _cache:
        _cache["industry_signals"] = [s for s in _cache["industry_signals"] if s.get("id") != sig_id]
    return deleted


def get_industry_signal_by_id(sig_id: str) -> dict | None:
    """Find industry signal by ID authoritatively from Supabase."""
    from app.repositories.supabase_repository import get_industry_signal
    return get_industry_signal(sig_id)


# ---------------------------------------------------------------------------
# Phase 32F: Authoritative Supabase persistence for skill_forecasts
# ---------------------------------------------------------------------------

def save_skill_forecast(forecast_data: dict) -> dict:
    """Save or insert skill forecast authoritatively into Supabase."""
    from app.repositories.supabase_repository import create_skill_forecast
    saved = create_skill_forecast(forecast_data)
    if "skill_forecasts" in _cache:
        forecasts = _cache["skill_forecasts"]
        idx = next((i for i, f in enumerate(forecasts) if f.get("id") == saved.get("id")), None)
        if idx is not None:
            forecasts[idx] = saved
        else:
            forecasts.insert(0, saved)
    return saved


def update_skill_forecast(forecast_id: str, updates: dict) -> dict | None:
    """Update fields on a skill forecast record authoritatively in Supabase."""
    from app.repositories.supabase_repository import update_skill_forecast_repo, SkillForecastNotFoundError
    try:
        updated = update_skill_forecast_repo(forecast_id, updates)
        if "skill_forecasts" in _cache:
            for f in _cache["skill_forecasts"]:
                if f.get("id") == forecast_id:
                    f.update(updated)
                    break
        return updated
    except SkillForecastNotFoundError:
        return None


def delete_skill_forecast(forecast_id: str) -> bool:
    """Delete skill forecast authoritatively from Supabase."""
    from app.repositories.supabase_repository import delete_skill_forecast_repo
    deleted = delete_skill_forecast_repo(forecast_id)
    if "skill_forecasts" in _cache:
        _cache["skill_forecasts"] = [f for f in _cache["skill_forecasts"] if f.get("id") != forecast_id]
    return deleted


def get_skill_forecast_by_id(forecast_id: str) -> dict | None:
    """Find skill forecast by ID authoritatively from Supabase."""
    from app.repositories.supabase_repository import get_skill_forecast
    return get_skill_forecast(forecast_id)


# ---------------------------------------------------------------------------
# Phase 23: User Identity & Authentication Persistence
# ---------------------------------------------------------------------------

def init_demo_users():
    """Ensure baseline demo accounts exist for each role with bcrypt hashed passwords."""
    users = _cache.setdefault("users", [])
    existing_emails = {u.get("email", "").lower() for u in users if isinstance(u, dict)}

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
    for acc in demo_accounts:
        if acc["email"].lower() not in existing_emails:
            users.append(acc)
            existing_emails.add(acc["email"].lower())


def get_user_by_email(email: str) -> dict | None:
    """Find user record by case-insensitive email address."""
    if not _cache:
        init_db()
    if not any(u.get("id") == "usr-student-001" for u in _cache.get("users", [])):
        init_demo_users()
    users = _cache.get("users", [])
    clean_email = email.strip().lower()
    for u in users:
        if u.get("email", "").strip().lower() == clean_email:
            return u
    return None


def get_user_by_id(user_id: str) -> dict | None:
    """Find user record by ID."""
    if not _cache:
        init_db()
    if not any(u.get("id") == "usr-student-001" for u in _cache.get("users", [])):
        init_demo_users()
    users = _cache.get("users", [])
    for u in users:
        if u.get("id") == user_id:
            return u
    return None


def list_users() -> list[dict]:
    """Return all user accounts."""
    if not _cache:
        init_db()
    if not any(u.get("id") == "usr-student-001" for u in _cache.get("users", [])):
        init_demo_users()
    return _cache.get("users", [])


def save_user(user_data: dict) -> dict:
    """Save or update user record in memory cache, local real storage, and Supabase."""
    if not _cache:
        init_db()
    now_iso = datetime.now(timezone.utc).isoformat()
    user_data.setdefault("created_at", now_iso)
    user_data["updated_at"] = now_iso
    user_data.setdefault("source", "USER_SUBMITTED")
    user_data["is_demo"] = False
    client = get_supabase_client()
    if client:
        try:
            client.table("users").upsert(user_data).execute()
            logger.info("[DB] Persisted user '%s' (%s) to Supabase.", user_data.get("email"), user_data.get("role"))
        except Exception as e:
            logger.error("[DB] Failed persisting user to Supabase: %s", e)
            from app.repositories.supabase_repository import SupabaseRepositoryError
            raise SupabaseRepositoryError(f"Database persistence failed for user: {e}") from e

    users = _cache.setdefault("users", [])
    existing_idx = next((i for i, u in enumerate(users) if u.get("id") == user_data.get("id") or u.get("email", "").lower() == user_data.get("email", "").lower()), None)
    if existing_idx is not None:
        users[existing_idx] = user_data
    else:
        users.append(user_data)

    _flush_real_table("users")
    return user_data


# Re-export centralized demo student helper for convenience
from app.core.security import is_demo_student_id  # noqa: E402

