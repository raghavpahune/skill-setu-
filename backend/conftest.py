"""Pytest configuration and Supabase test doubles for SkillSetu backend test suites."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any
import pytest

from app.repositories.supabase_repository import set_supabase_client, reset_supabase_client


class MockSupabaseQuery:
    def __init__(self, table: MockSupabaseTable):
        self.table = table
        self.filters: list[tuple[str, Any]] = []
        self._action = "select"
        self._mutation_data: Any | None = None

    def select(self, columns="*"):
        self._action = "select"
        return self

    def update(self, updates: dict):
        self._action = "update"
        self._mutation_data = updates
        return self

    def insert(self, data: Any):
        self._action = "insert"
        self._mutation_data = data
        return self

    def upsert(self, data: Any):
        self._action = "upsert"
        self._mutation_data = data
        return self

    def delete(self):
        self._action = "delete"
        return self

    def eq(self, column: str, value: Any):
        self.filters.append((column, value))
        return self

    def execute(self):
        if (
            self.table.should_fail
            or (self._action == "update" and self.table.should_fail_update)
            or (self._action == "select" and self.table.should_fail_select)
            or (self._action in ("insert", "upsert") and self.table.should_fail_insert)
            or (self._action == "delete" and self.table.should_fail_delete)
        ):
            raise RuntimeError("Simulated Supabase PostgreSQL database connection error")

        if self._action in ("insert", "upsert"):
            items = [self._mutation_data] if isinstance(self._mutation_data, dict) else list(self._mutation_data)
            result_rows = []
            for item in items:
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
                match = True
                for col, val in self.filters:
                    if str(row.get(col, "")).lower() != str(val).lower():
                        match = False
                        break
                if match:
                    deleted_rows.append(row)
                else:
                    surviving_rows.append(row)
            self.table.rows = surviving_rows
            return type("APIResponse", (), {"data": deepcopy(deleted_rows), "count": len(deleted_rows)})()

        # Filter matching rows for select & update
        matching_rows = []
        matching_indices = []
        for idx, row in enumerate(self.table.rows):
            match = True
            for col, val in self.filters:
                if str(row.get(col, "")).lower() != str(val).lower():
                    match = False
                    break
            if match:
                matching_rows.append(row)
                matching_indices.append(idx)

        if self._action == "select":
            return type("APIResponse", (), {"data": deepcopy(matching_rows), "count": len(matching_rows)})()
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

    def insert(self, data: Any):
        return MockSupabaseQuery(self).insert(data)

    def upsert(self, data: Any):
        return MockSupabaseQuery(self).upsert(data)

    def delete(self):
        return MockSupabaseQuery(self).delete()


class MockSupabaseClient:
    def __init__(self, feedback_rows=None, demands_rows=None, profiles_rows=None, assessments_rows=None):
        self.tables = {
            "employer_feedback": MockSupabaseTable(feedback_rows),
            "employer_demands": MockSupabaseTable(demands_rows),
            "student_profiles": MockSupabaseTable(profiles_rows),
            "student_assessments": MockSupabaseTable(assessments_rows),
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


@pytest.fixture(autouse=True)
def mock_supabase_for_tests():
    """Autouse fixture providing an isolated Supabase test double for unit test suites."""
    mock_client = MockSupabaseClient(
        feedback_rows=_load_demo_feedback_rows(),
        demands_rows=_load_initial_demands_rows(),
        profiles_rows=_load_initial_student_profiles_rows(),
        assessments_rows=_load_initial_student_assessments_rows(),
    )
    set_supabase_client(mock_client)
    yield mock_client
    reset_supabase_client()
