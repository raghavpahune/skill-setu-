"""Pytest configuration and Supabase test doubles for SkillSetu backend test suites."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
import pytest

from app.repositories.supabase_repository import set_supabase_client, reset_supabase_client
from app.config import settings


class MockSupabaseQuery:
    def __init__(self, table: MockSupabaseTable):
        self.table = table
        self.filters: list[tuple[str, any]] = []
        self._action = "select"
        self._update_data: dict | None = None

    def select(self, columns="*"):
        self._action = "select"
        return self

    def update(self, updates: dict):
        self._action = "update"
        self._update_data = updates
        return self

    def eq(self, column: str, value: any):
        self.filters.append((column, value))
        return self

    def execute(self):
        if self.table.should_fail or (self._action == "update" and self.table.should_fail_update) or (self._action == "select" and self.table.should_fail_select):
            raise RuntimeError("Simulated Supabase PostgreSQL database connection error")

        matching_rows = []
        matching_indices = []
        for idx, row in enumerate(self.table.rows):
            match = True
            for col, val in self.filters:
                row_val = str(row.get(col, "")).lower()
                target_val = str(val).lower()
                if row_val != target_val:
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
                row.update(deepcopy(self._update_data))
                updated_rows.append(deepcopy(row))
            return type("APIResponse", (), {"data": updated_rows, "count": len(updated_rows)})()
        return type("APIResponse", (), {"data": [], "count": 0})()


class MockSupabaseTable:
    def __init__(self, initial_rows=None):
        self.rows = deepcopy(initial_rows) if initial_rows else []
        self.should_fail = False
        self.should_fail_update = False
        self.should_fail_select = False

    def select(self, columns="*"):
        q = MockSupabaseQuery(self)
        return q.select(columns)

    def update(self, updates: dict):
        q = MockSupabaseQuery(self)
        return q.update(updates)


class MockSupabaseClient:
    def __init__(self, feedback_rows=None):
        self.tables = {
            "employer_feedback": MockSupabaseTable(feedback_rows)
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


@pytest.fixture(autouse=True)
def mock_supabase_for_tests():
    """Autouse fixture providing an isolated Supabase test double for unit test suites."""
    # Only mock if not pointing to a real Supabase production instance
    mock_client = MockSupabaseClient(_load_demo_feedback_rows())
    set_supabase_client(mock_client)
    yield mock_client
    reset_supabase_client()
