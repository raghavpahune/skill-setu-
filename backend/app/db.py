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
            "skill_forecasts", "student_profiles", "schemes", "sync_logs"
        ]
        for tbl in tables:
            try:
                res = client.table(tbl).select("*").execute()
                if res.data and len(res.data) > 0:
                    _cache[tbl] = res.data
                    logger.info("[DB] Loaded %d records from Supabase table '%s'", len(res.data), tbl)
            except Exception as e:
                logger.warning("[DB] Supabase table '%s' query error: %s", tbl, e)


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
