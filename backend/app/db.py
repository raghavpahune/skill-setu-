"""Demo data loader — serves JSON files from data/demo/ when Supabase is not connected."""
import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "demo"
_cache: dict[str, list] = {}


def load_demo_data():
    """Load all demo JSON files into memory cache."""
    for f in _DATA_DIR.glob("*.json"):
        _cache[f.stem] = json.loads(f.read_text(encoding="utf-8"))


def get_demo(table: str) -> list[dict]:
    """Get demo data for a table name. Returns empty list if not loaded."""
    return _cache.get(table, [])


def set_demo(table: str, data: list[dict]):
    """Set demo data for a table name."""
    _cache[table] = data


def append_demo(table: str, record: dict):
    """Append a single record to the cached table."""
    if table not in _cache:
        _cache[table] = []
    _cache[table].append(record)
