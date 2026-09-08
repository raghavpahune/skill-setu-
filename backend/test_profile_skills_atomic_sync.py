import re
import sqlite3
import uuid
from copy import deepcopy
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.db import save_user
from app.repositories import supabase_repository
from app.repositories.supabase_repository import (
    SupabaseRepositoryError,
    get_client,
    get_student_profile,
    upsert_student_profile,
)
from app.core.security import create_access_token


def _get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def test_atomic_rollback_when_skills_sync_fails():
    client = get_client()
    user_id = f"usr-atomic-{uuid.uuid4().hex[:8]}"
    skill_a = str(uuid.uuid4())
    skill_b = str(uuid.uuid4())
    skill_c = str(uuid.uuid4())

    initial_payload = {
        "user_id": user_id,
        "full_name": "Test Student",
        "target_role": "Backend Engineer",
        "skills": [
            {"skill_id": skill_a, "skill_name": "Python", "proficiency": "intermediate"},
            {"skill_id": skill_b, "skill_name": "PostgreSQL", "proficiency": "advanced"},
        ],
        "is_demo": False,
    }
    saved_initial = upsert_student_profile(initial_payload)
    assert len(saved_initial["skills"]) == 2

    initial_prof_rows = [r for r in client.table("student_profiles").rows if r.get("user_id") == user_id]
    initial_skills_rows = [r for r in client.table("student_skills").rows if r.get("user_id") == user_id]
    assert len(initial_prof_rows) == 1
    assert len(initial_skills_rows) == 2

    client.table("student_skills").should_fail_insert = True

    updated_payload = {
        "user_id": user_id,
        "full_name": "Test Student Modified",
        "target_role": "Principal Engineer",
        "skills": [
            {"skill_id": skill_a, "skill_name": "Python", "proficiency": "intermediate"},
            {"skill_id": skill_b, "skill_name": "PostgreSQL", "proficiency": "advanced"},
            {"skill_id": skill_c, "skill_name": "Distributed Systems", "proficiency": "advanced"},
        ],
        "is_demo": False,
    }

    with pytest.raises(SupabaseRepositoryError):
        upsert_student_profile(updated_payload)

    client.table("student_skills").should_fail_insert = False

    after_prof_rows = [r for r in client.table("student_profiles").rows if r.get("user_id") == user_id]
    after_skills_rows = [r for r in client.table("student_skills").rows if r.get("user_id") == user_id]

    assert len(after_prof_rows) == 1
    assert after_prof_rows[0]["target_role"] == "Backend Engineer"
    assert len(after_prof_rows[0]["skills"]) == 2

    skill_ids_in_prof = {s["skill_id"] for s in after_prof_rows[0]["skills"]}
    assert skill_ids_in_prof == {skill_a, skill_b}
    assert skill_c not in skill_ids_in_prof

    skill_ids_in_table = {r["skill_id"] for r in after_skills_rows}
    assert skill_ids_in_table == {skill_a, skill_b}
    assert skill_c not in skill_ids_in_table


def test_atomic_rollback_via_api_endpoint():
    client_db = get_client()
    user_id = "test-student-atomic-api"
    save_user({
        "id": user_id,
        "email": "student-atomic@skillsetu.gov.in",
        "role": "STUDENT",
        "full_name": "API Student",
        "name": "API Student",
    })
    token = create_access_token(data={"sub": user_id, "role": "STUDENT", "email": "student-atomic@skillsetu.gov.in"})
    headers = {"Authorization": f"Bearer {token}"}

    skill_a = str(uuid.uuid4())
    skill_b = str(uuid.uuid4())
    skill_c = str(uuid.uuid4())

    upsert_student_profile({
        "user_id": user_id,
        "full_name": "API Student",
        "target_role": "Data Engineer",
        "skills": [
            {"skill_id": skill_a, "skill_name": "Python", "proficiency": "intermediate"},
            {"skill_id": skill_b, "skill_name": "SQL", "proficiency": "intermediate"},
        ],
        "is_demo": False,
    })

    client_db.table("student_skills").should_fail_insert = True

    api_client = TestClient(app)
    resp = api_client.put(
        "/api/student/profile",
        json={
            "target_role": "Lead Data Engineer",
            "skills": [
                {"skill_id": skill_a, "skill_name": "Python", "proficiency": "advanced"},
                {"skill_id": skill_b, "skill_name": "SQL", "proficiency": "advanced"},
                {"skill_id": skill_c, "skill_name": "Spark", "proficiency": "beginner"},
            ],
        },
        headers=headers,
    )

    client_db.table("student_skills").should_fail_insert = False

    assert resp.status_code == 500
    assert "Database persistence failed" in resp.json()["detail"]

    current_profile = get_student_profile(user_id)
    assert current_profile is not None
    assert current_profile["target_role"] == "Data Engineer"
    assert len(current_profile["skills"]) == 2
    current_sids = {s["skill_id"] for s in current_profile["skills"]}
    assert current_sids == {skill_a, skill_b}


def test_atomic_sync_success_and_diff():
    user_id = f"usr-success-{uuid.uuid4().hex[:8]}"
    skill_a = str(uuid.uuid4())
    skill_b = str(uuid.uuid4())
    skill_c = str(uuid.uuid4())

    initial_payload = {
        "user_id": user_id,
        "full_name": "Success Student",
        "target_role": "Frontend Developer",
        "skills": [
            {"skill_id": skill_a, "skill_name": "HTML", "proficiency": "beginner"},
            {"skill_id": skill_b, "skill_name": "CSS", "proficiency": "intermediate"},
        ],
        "is_demo": False,
    }
    upsert_student_profile(initial_payload)

    updated_payload = {
        "user_id": user_id,
        "full_name": "Success Student",
        "target_role": "Fullstack Developer",
        "skills": [
            {"skill_id": skill_b, "skill_name": "CSS", "proficiency": "advanced"},
            {"skill_id": skill_c, "skill_name": "TypeScript", "proficiency": "intermediate"},
        ],
        "is_demo": False,
    }
    saved_updated = upsert_student_profile(updated_payload)

    assert saved_updated["target_role"] == "Fullstack Developer"
    assert len(saved_updated["skills"]) == 2
    updated_sids = {s["skill_id"] for s in saved_updated["skills"]}
    assert updated_sids == {skill_b, skill_c}
    assert skill_a not in updated_sids

    client = get_client()
    table_rows = [r for r in client.table("student_skills").rows if r.get("user_id") == user_id]
    assert len(table_rows) == 2
    table_sids = {r["skill_id"] for r in table_rows}
    assert table_sids == {skill_b, skill_c}
    assert skill_a not in table_sids

    b_row = next(r for r in table_rows if r["skill_id"] == skill_b)
    assert b_row["proficiency"] == "advanced"


def test_atomic_sync_idempotency():
    user_id = f"usr-idemp-{uuid.uuid4().hex[:8]}"
    skill_a = str(uuid.uuid4())
    skill_b = str(uuid.uuid4())

    payload = {
        "user_id": user_id,
        "full_name": "Idempotent Student",
        "target_role": "Security Engineer",
        "skills": [
            {"skill_id": skill_a, "skill_name": "Network Security", "proficiency": "intermediate"},
            {"skill_id": skill_b, "skill_name": "Cryptography", "proficiency": "advanced"},
        ],
        "is_demo": False,
    }

    first = upsert_student_profile(payload)
    second = upsert_student_profile(payload)

    assert first["user_id"] == second["user_id"]
    assert len(first["skills"]) == len(second["skills"]) == 2

    client = get_client()
    table_rows = [r for r in client.table("student_skills").rows if r.get("user_id") == user_id]
    assert len(table_rows) == 2


def test_sqlite_transactional_atomicity_guarantee():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            role TEXT NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE skills (
            id TEXT PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE student_profiles (
            user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            target_role TEXT NOT NULL,
            skills_json TEXT NOT NULL
        );
    """)
    cursor.execute("""
        CREATE TABLE student_skills (
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            skill_id TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
            proficiency TEXT NOT NULL,
            PRIMARY KEY (user_id, skill_id)
        );
    """)
    conn.commit()

    user_id = "usr-sql-test-1"
    skill_a = "sk-uuid-1"
    skill_b = "sk-uuid-2"
    skill_invalid = "sk-non-existent"

    cursor.execute("INSERT INTO users VALUES (?, ?)", (user_id, "STUDENT"))
    cursor.execute("INSERT INTO skills VALUES (?, ?)", (skill_a, "Python"))
    cursor.execute("INSERT INTO skills VALUES (?, ?)", (skill_b, "Postgres"))
    cursor.execute("INSERT INTO student_profiles VALUES (?, ?, ?)", (user_id, "Junior Dev", '["Python", "Postgres"]'))
    cursor.execute("INSERT INTO student_skills VALUES (?, ?, ?)", (user_id, skill_a, "intermediate"))
    cursor.execute("INSERT INTO student_skills VALUES (?, ?, ?)", (user_id, skill_b, "intermediate"))
    conn.commit()

    conn.isolation_level = None
    cursor.execute("BEGIN TRANSACTION;")
    cursor.execute("UPDATE student_profiles SET target_role = ?, skills_json = ? WHERE user_id = ?", ("Senior Dev", '["Python", "Postgres", "Invalid"]', user_id))

    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute("INSERT INTO student_skills VALUES (?, ?, ?)", (user_id, skill_invalid, "beginner"))

    cursor.execute("ROLLBACK;")

    cursor.execute("SELECT target_role, skills_json FROM student_profiles WHERE user_id = ?", (user_id,))
    prof_row = cursor.fetchone()
    assert prof_row[0] == "Junior Dev"
    assert prof_row[1] == '["Python", "Postgres"]'

    cursor.execute("SELECT COUNT(*) FROM student_skills WHERE user_id = ?", (user_id,))
    assert cursor.fetchone()[0] == 2

    conn.close()


def test_migration_and_schema_rpc_contract():
    migration_file = _get_project_root() / "data" / "migrations" / "20260909_atomic_student_profile_and_skills_sync.sql"
    assert migration_file.is_file()
    mig_content = migration_file.read_text(encoding="utf-8")

    assert "CREATE OR REPLACE FUNCTION public.sync_student_profile_atomic" in mig_content
    assert "SECURITY DEFINER" in mig_content
    assert "SET search_path = public, pg_temp" in mig_content
    assert "REVOKE ALL ON FUNCTION public.sync_student_profile_atomic(JSONB) FROM PUBLIC" in mig_content
    assert "GRANT EXECUTE ON FUNCTION public.sync_student_profile_atomic(JSONB) TO authenticated, service_role" in mig_content
    assert "DELETE FROM public.student_skills" in mig_content
    assert "INSERT INTO public.student_skills" in mig_content
    assert "ON CONFLICT (user_id, skill_id) DO UPDATE SET" in mig_content

    schema_file = _get_project_root() / "data" / "schema.sql"
    schema_content = schema_file.read_text(encoding="utf-8")
    assert "CREATE OR REPLACE FUNCTION public.sync_student_profile_atomic" in schema_content
    assert "SECURITY DEFINER" in schema_content
    assert "GRANT EXECUTE ON FUNCTION public.sync_student_profile_atomic(JSONB) TO authenticated, service_role" in schema_content
