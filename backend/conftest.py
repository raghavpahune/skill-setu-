"""Pytest configuration and Supabase test doubles for SkillSetu backend test suites."""
from __future__ import annotations

import os
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-dedicated-for-pytest-conftest-environment")

import json
from copy import deepcopy
from pathlib import Path
from typing import Any
import pytest

from app.config import settings
if not settings.jwt_secret_key:
    settings.jwt_secret_key = "test-secret-key-dedicated-for-pytest-conftest-environment"

from app.repositories.supabase_repository import set_supabase_client, reset_supabase_client


class MockSupabaseQuery:
    def __init__(self, table: MockSupabaseTable):
        self.table = table
        self.filters: list[tuple[str, Any]] = []
        self._in_filters: list[tuple[str, list[Any]]] = []
        self._ilike_filters: list[tuple[str, str]] = []
        self._action = "select"
        self._mutation_data: Any | None = None

    def select(self, columns="*"):
        self._action = "select"
        return self

    def update(self, updates: dict):
        self._action = "update"
        self._mutation_data = updates
        return self

    def insert(self, data: Any, *args: Any, **kwargs: Any):
        self._action = "insert"
        self._mutation_data = data
        return self

    def upsert(self, data: Any, *args: Any, **kwargs: Any):
        self._action = "upsert"
        self._mutation_data = data
        self._on_conflict = kwargs.get("on_conflict")
        return self

    def delete(self):
        self._action = "delete"
        return self

    def eq(self, column: str, value: Any):
        self.filters.append((column, value))
        return self

    def in_(self, column: str, values: list[Any]):
        self._in_filters.append((column, list(values)))
        return self

    def ilike(self, column: str, pattern: str):
        self._ilike_filters.append((column, pattern))
        return self

    def range(self, start: int, end: int):
        self._range = (start, end)
        return self

    def limit(self, count: int):
        self._limit = count
        return self

    def execute(self):
        import re

        if (
            self.table.should_fail
            or (self._action == "update" and self.table.should_fail_update)
            or (self._action == "select" and self.table.should_fail_select)
            or (self._action in ("insert", "upsert") and self.table.should_fail_insert)
            or (self._action == "delete" and self.table.should_fail_delete)
        ):
            raise RuntimeError("Simulated Supabase PostgreSQL database connection error")

        def matches_filters(row: dict) -> bool:
            for col, val in self.filters:
                if str(row.get(col, "")).lower() != str(val).lower():
                    return False
            for col, vals in getattr(self, "_in_filters", []):
                if row.get(col) not in vals:
                    return False
            for col, pattern in getattr(self, "_ilike_filters", []):
                val = str(row.get(col, "")).lower()
                raw_pat = pattern.lower().replace(r"\%", "\x00").replace(r"\_", "\x01")
                escaped = re.escape(raw_pat)
                pat = "^" + escaped.replace("%", ".*").replace("_", ".").replace("\x00", "%").replace("\x01", "_") + "$"
                if not re.search(pat, val):
                    return False
            return True

        if self._action in ("insert", "upsert"):
            items = [self._mutation_data] if isinstance(self._mutation_data, dict) else list(self._mutation_data)
            result_rows = []
            on_conflict_cols = [c.strip() for c in (getattr(self, "_on_conflict", None) or "").split(",") if c.strip()]
            for item in items:
                idx = None
                if on_conflict_cols:
                    idx = next(
                        (
                            i
                            for i, r in enumerate(self.table.rows)
                            if all(
                                item.get(c) is not None
                                and r.get(c) is not None
                                and r.get(c) == item.get(c)
                                for c in on_conflict_cols
                            )
                        ),
                        None,
                    )
                if idx is None:
                    item_id = item.get("id")
                    idx = next((i for i, r in enumerate(self.table.rows) if item_id and r.get("id") == item_id), None)
                if idx is not None:
                    self.table.rows[idx].update(deepcopy(item))
                    result_rows.append(deepcopy(self.table.rows[idx]))
                else:
                    new_row = deepcopy(item)
                    self.table.rows.append(new_row)
                    result_rows.append(new_row)
            return type("APIResponse", (), {"data": result_rows, "count": len(result_rows)})()

        if self._action == "delete":
            deleted_rows = []
            surviving_rows = []
            for row in self.table.rows:
                if matches_filters(row):
                    deleted_rows.append(row)
                else:
                    surviving_rows.append(row)
            self.table.rows = surviving_rows
            return type("APIResponse", (), {"data": deepcopy(deleted_rows), "count": len(deleted_rows)})()

        # Filter matching rows for select & update
        matching_rows = []
        matching_indices = []
        for idx, row in enumerate(self.table.rows):
            if matches_filters(row):
                matching_rows.append(row)
                matching_indices.append(idx)

        if self._action == "select":
            selected_rows = deepcopy(matching_rows)
            if hasattr(self, "_range") and self._range is not None:
                start, end = self._range
                selected_rows = selected_rows[start : end + 1]
            elif hasattr(self, "_limit") and self._limit is not None:
                selected_rows = selected_rows[: self._limit]
            return type("APIResponse", (), {"data": selected_rows, "count": len(selected_rows)})()
        elif self._action == "update":
            updated_rows = []
            for idx in matching_indices:
                row = self.table.rows[idx]
                row.update(deepcopy(self._mutation_data))
                updated_rows.append(deepcopy(row))
            return type("APIResponse", (), {"data": updated_rows, "count": len(updated_rows)})()

        return type("APIResponse", (), {"data": [], "count": 0})()


class MockSupabaseTable:
    def __init__(self, initial_rows=None):
        self.rows: list[dict[str, Any]] = deepcopy(initial_rows) if initial_rows else []
        self.should_fail = False
        self.should_fail_update = False
        self.should_fail_select = False
        self.should_fail_insert = False
        self.should_fail_delete = False

    def select(self, columns="*"):
        return MockSupabaseQuery(self).select(columns)

    def update(self, updates: dict):
        return MockSupabaseQuery(self).update(updates)

    def insert(self, data: Any, *args: Any, **kwargs: Any):
        return MockSupabaseQuery(self).insert(data, *args, **kwargs)

    def upsert(self, data: Any, *args: Any, **kwargs: Any):
        return MockSupabaseQuery(self).upsert(data, *args, **kwargs)

    def delete(self):
        return MockSupabaseQuery(self).delete()


class MockSupabaseClient:
    def __init__(self, feedback_rows=None, demands_rows=None, profiles_rows=None, assessments_rows=None, courses_rows=None, industry_signals_rows=None, skill_forecasts_rows=None, schemes_rows=None, gov_opportunities_rows=None):
        self.tables = {
            "employer_feedback": MockSupabaseTable(feedback_rows),
            "employer_demands": MockSupabaseTable(demands_rows),
            "student_profiles": MockSupabaseTable(profiles_rows),
            "student_assessments": MockSupabaseTable(assessments_rows),
            "courses": MockSupabaseTable(courses_rows),
            "industry_signals": MockSupabaseTable(industry_signals_rows),
            "skill_forecasts": MockSupabaseTable(skill_forecasts_rows),
            "schemes": MockSupabaseTable(schemes_rows),
            "gov_opportunities": MockSupabaseTable(gov_opportunities_rows),
        }

    def table(self, table_name: str) -> MockSupabaseTable:
        if table_name not in self.tables:
            self.tables[table_name] = MockSupabaseTable([])
        return self.tables[table_name]


def _load_demo_feedback_rows() -> list[dict]:
    demo_file = Path(__file__).resolve().parent.parent / "data" / "demo" / "employer_feedback.json"
    if demo_file.is_file():
        try:
            return json.loads(demo_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return [
        {"id": "ef-001", "employer_id": "emp-001", "skill_id": "sk-005", "demand_level": "critical", "proficiency_required": "advanced", "status": "pending", "notes": None},
        {"id": "ef-002", "employer_id": "emp-001", "skill_id": "sk-004", "demand_level": "high", "proficiency_required": "intermediate", "status": "confirmed", "notes": "Gen AI skills"},
        {"id": "ef-004", "employer_id": "emp-002", "skill_id": "sk-002", "demand_level": "high", "proficiency_required": "advanced", "status": "confirmed", "notes": None},
    ]


def _load_initial_demands_rows() -> list[dict]:
    rows: list[dict] = []
    base_dir = Path(__file__).resolve().parent.parent / "data"
    demo_file = base_dir / "demo" / "employer_demands.json"
    real_file = base_dir / "real" / "employer_demands.json"

    seen_ids = set()
    for file_path in (real_file, demo_file):
        if file_path.is_file():
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                for d in data:
                    if d.get("id") and d["id"] not in seen_ids:
                        rows.append(d)
                        seen_ids.add(d["id"])
            except Exception:
                pass
    return rows


def _load_initial_student_profiles_rows() -> list[dict]:
    rows: list[dict] = []
    base_dir = Path(__file__).resolve().parent.parent / "data"
    demo_file = base_dir / "demo" / "student_profiles.json"
    real_file = base_dir / "real" / "student_profiles.json"

    seen_ids = set()
    for file_path in (real_file, demo_file):
        if file_path.is_file():
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                for p in data:
                    pid = p.get("user_id") or p.get("id")
                    if pid and pid not in seen_ids:
                        rows.append(p)
                        seen_ids.add(pid)
            except Exception:
                pass
    return rows


def _load_initial_student_assessments_rows() -> list[dict]:
    rows: list[dict] = []
    base_dir = Path(__file__).resolve().parent.parent / "data"
    demo_file = base_dir / "demo" / "student_assessments.json"
    real_file = base_dir / "real" / "student_assessments.json"

    seen_ids = set()
    for file_path in (real_file, demo_file):
        if file_path.is_file():
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                for a in data:
                    aid = a.get("id")
                    if aid and aid not in seen_ids:
                        rows.append(a)
                        seen_ids.add(aid)
            except Exception:
                pass
    return rows


def _load_initial_courses_rows() -> list[dict]:
    rows: list[dict] = []
    base_dir = Path(__file__).resolve().parent.parent / "data"
    demo_file = base_dir / "demo" / "courses.json"
    real_file = base_dir / "real" / "courses.json"

    seen_ids = set()
    for file_path in (real_file, demo_file):
        if file_path.is_file():
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                for c in data:
                    cid = c.get("id")
                    if cid and cid not in seen_ids:
                        rows.append(c)
                        seen_ids.add(cid)
            except Exception:
                pass
    return rows


def _load_initial_industry_signals_rows() -> list[dict]:
    rows: list[dict] = []
    base_dir = Path(__file__).resolve().parent.parent / "data"
    demo_file = base_dir / "demo" / "industry_signals.json"
    real_file = base_dir / "real" / "industry_signals.json"

    seen_ids = set()
    for file_path in (real_file, demo_file):
        if file_path.is_file():
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                for s in data:
                    sid = s.get("id")
                    if sid and sid not in seen_ids:
                        rows.append(s)
                        seen_ids.add(sid)
            except Exception:
                pass
    return rows


def _load_initial_skill_forecasts_rows() -> list[dict]:
    rows: list[dict] = []
    base_dir = Path(__file__).resolve().parent.parent / "data"
    demo_file = base_dir / "demo" / "skill_forecasts.json"
    real_file = base_dir / "real" / "skill_forecasts.json"

    seen_ids = set()
    for file_path in (real_file, demo_file):
        if file_path.is_file():
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                for s in data:
                    sid = s.get("id")
                    if sid and sid not in seen_ids:
                        rows.append(s)
                        seen_ids.add(sid)
            except Exception:
                pass
    return rows


def _load_initial_gov_opportunities_rows() -> list[dict]:
    rows: list[dict] = []
    base_dir = Path(__file__).resolve().parent.parent / "data"
    demo_file = base_dir / "demo" / "gov_opportunities.json"
    real_file = base_dir / "real" / "gov_opportunities.json"

    seen_ids = set()
    for file_path in (real_file, demo_file):
        if file_path.is_file():
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                for o in data:
                    oid = o.get("id")
                    if oid and oid not in seen_ids:
                        rows.append(o)
                        seen_ids.add(oid)
            except Exception:
                pass
    return rows


_PRISTINE_FEEDBACK = deepcopy(_load_demo_feedback_rows())
_PRISTINE_DEMANDS = deepcopy(_load_initial_demands_rows())
_PRISTINE_PROFILES = deepcopy(_load_initial_student_profiles_rows())
_PRISTINE_ASSESSMENTS = deepcopy(_load_initial_student_assessments_rows())
_PRISTINE_COURSES = deepcopy(_load_initial_courses_rows())
_PRISTINE_SIGNALS = deepcopy(_load_initial_industry_signals_rows())
_PRISTINE_FORECASTS = deepcopy(_load_initial_skill_forecasts_rows())
_PRISTINE_GOV_OPPORTUNITIES = deepcopy(_load_initial_gov_opportunities_rows())


@pytest.fixture(scope="session", autouse=True)
def preserve_real_disk_files():
    """Snapshot and restore data/real/*.json before and after the test session."""
    real_dir = Path(__file__).resolve().parent.parent / "data" / "real"
    snapshots = {}
    if real_dir.is_dir():
        for f in real_dir.glob("*.json"):
            try:
                snapshots[f] = f.read_bytes()
            except Exception:
                pass
    yield
    for f, content in snapshots.items():
        try:
            f.write_bytes(content)
        except Exception:
            pass


@pytest.fixture(autouse=True)
def mock_supabase_for_tests():
    """Autouse fixture providing an isolated Supabase test double for unit test suites."""
    from app.db import _cache, load_demo_data, load_real_data, init_demo_users
    for tbl in ("skills", "jobs", "schemes", "gov_opportunities"):
        if tbl not in _cache or not _cache[tbl]:
            load_demo_data()
            break
    load_real_data()
    init_demo_users()

    mock_client = MockSupabaseClient(
        feedback_rows=deepcopy(_PRISTINE_FEEDBACK),
        demands_rows=deepcopy(_PRISTINE_DEMANDS),
        profiles_rows=deepcopy(_PRISTINE_PROFILES),
        assessments_rows=deepcopy(_PRISTINE_ASSESSMENTS),
        courses_rows=deepcopy(_PRISTINE_COURSES),
        industry_signals_rows=deepcopy(_PRISTINE_SIGNALS),
        skill_forecasts_rows=deepcopy(_PRISTINE_FORECASTS),
        schemes_rows=deepcopy(_cache.get("schemes", [])),
        gov_opportunities_rows=deepcopy(_PRISTINE_GOV_OPPORTUNITIES),
    )
    set_supabase_client(mock_client)
    yield mock_client
    reset_supabase_client()
