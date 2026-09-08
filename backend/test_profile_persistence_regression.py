import pytest
from starlette.testclient import TestClient

from app.main import app
from app.core.security import create_access_token
from app.repositories import supabase_repository
from app.repositories.supabase_repository import (
    upsert_student_profile,
    get_student_profile,
    delete_student_profile,
    SupabaseRepositoryError,
)

from app.db import save_user

STUDENT_TOKEN = create_access_token({"sub": "usr-student-reg-001", "email": "student.reg@skillsetu.gov.in", "role": "STUDENT"})
STUDENT_HEADERS = {"Authorization": f"Bearer {STUDENT_TOKEN}"}
EMPLOYER_TOKEN = create_access_token({"sub": "usr-emp-reg-001", "email": "emp.reg@company.com", "role": "EMPLOYER"})
EMPLOYER_HEADERS = {"Authorization": f"Bearer {EMPLOYER_TOKEN}"}


@pytest.fixture(autouse=True)
def setup_test_users():
    save_user({
        "id": "usr-student-reg-001",
        "email": "student.reg@skillsetu.gov.in",
        "role": "STUDENT",
        "full_name": "Registered Student",
        "name": "Registered Student",
    })
    save_user({
        "id": "usr-emp-reg-001",
        "email": "emp.reg@company.com",
        "role": "EMPLOYER",
        "full_name": "Registered Employer",
        "name": "Registered Employer",
    })


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_no_column_pruning_on_schema_cache_mismatch_fails_closed():
    delete_student_profile("usr-student-reg-001")

    profile_data = {
        "user_id": "usr-student-reg-001",
        "full_name": "Adaptive Candidate",
        "target_role": "DevOps Engineer",
        "desired_role": "DevOps Engineer",
        "skills": [{"skill_name": "Python", "proficiency": "advanced"}],
        "skill_match_pct": 50,
    }

    client_mock = supabase_repository.get_client()
    original_upsert = client_mock.table("student_profiles").upsert

    failed_once = False

    def simulated_upsert(data, *args, **kwargs):
        nonlocal failed_once
        if not failed_once and "full_name" in data:
            failed_once = True
            raise RuntimeError("Could not find the 'full_name' column of 'student_profiles' in the schema cache")
        return original_upsert(data, *args, **kwargs)

    client_mock.table("student_profiles").upsert = simulated_upsert

    try:
        with pytest.raises(SupabaseRepositoryError):
            upsert_student_profile(profile_data)
        assert failed_once is True
    finally:
        client_mock.table("student_profiles").upsert = original_upsert


def test_student_profile_create_and_fetch_end_to_end(client):
    delete_student_profile("usr-student-reg-001")

    payload = {
        "institution": "VJTI Mumbai",
        "degree": "B.Tech Computer Science",
        "education_level": "Undergraduate",
        "academic_year": "Final Year",
        "graduation_year": 2026,
        "target_role": "Cloud Architect",
        "desired_role": "Cloud Architect",
        "preferred_location": "Mumbai",
        "career_interests": ["Cloud", "DevOps"],
        "skills": [{"skill_name": "AWS", "proficiency": "advanced"}],
        "projects": [{"name": "Cloud Infra", "description": "Terraform deploy", "skills": ["AWS"]}],
        "certifications": [{"name": "AWS Solutions Architect", "issuer": "Amazon", "issue_date": "2025-01-01"}],
        "courses": [{"course_name": "Cloud Native Architecture", "provider": "Coursera", "status": "completed"}],
    }

    create_resp = client.post("/api/student/profile", json=payload, headers=STUDENT_HEADERS)
    assert create_resp.status_code == 201
    created = create_resp.json()["profile"]
    assert created["user_id"] == "usr-student-reg-001"
    assert created["target_role"] == "Cloud Architect"

    get_resp = client.get("/api/student/profile", headers=STUDENT_HEADERS)
    assert get_resp.status_code == 200
    fetched = get_resp.json()["profile"]
    assert fetched["user_id"] == "usr-student-reg-001"
    assert len(fetched["skills"]) >= 1
    assert len(fetched["projects"]) >= 1


def test_unauthenticated_profile_access_is_rejected(client):
    resp = client.get("/api/student/profile")
    assert resp.status_code == 401


def test_employer_cannot_access_student_profile(client):
    resp = client.get("/api/student/profile", headers=EMPLOYER_HEADERS)
    assert resp.status_code == 403


def test_database_failure_propagates_clear_error_message(client, monkeypatch):
    def failing_upsert(*args, **kwargs):
        raise SupabaseRepositoryError("Database connection timed out during execution")

    monkeypatch.setattr(supabase_repository, "upsert_student_profile", failing_upsert)

    payload = {
        "target_role": "Cloud Architect",
        "skills": [{"skill_name": "Python", "proficiency": "intermediate"}],
    }
    resp = client.post("/api/student/profile", json=payload, headers=STUDENT_HEADERS)
    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert "Database persistence failed" in detail


def test_real_mode_does_not_fallback_to_stale_cache_when_not_in_database(monkeypatch):
    from app.config import settings
    from app.db import _cache
    from app.repositories.supabase_repository import get_client
    monkeypatch.setattr(settings, "use_demo_data", False)
    _cache["student_profiles"] = [{"user_id": "usr-ghost-1", "target_role": "Old Role"}]
    client_db = get_client()
    client_db.table("student_profiles").rows = []

    res = supabase_repository.get_student_profile("usr-ghost-1")
    assert res is None


def test_get_student_profile_does_not_merge_cache_when_in_database():
    from app.db import _cache
    client_db = supabase_repository.get_client()
    client_db.table("student_profiles").rows = [
        {"user_id": "usr-authoritative-1", "target_role": "Database Role"}
    ]
    _cache["student_profiles"] = [
        {"user_id": "usr-authoritative-1", "target_role": "Cache Role", "ghost_field": "unpersisted"}
    ]
    res = supabase_repository.get_student_profile("usr-authoritative-1")
    assert res is not None
    assert res["target_role"] == "Database Role"
    assert "ghost_field" not in res


def test_upsert_student_profile_raises_on_pgrst204():
    client_mock = supabase_repository.get_client()
    original_upsert = client_mock.table("student_profiles").upsert

    def simulated_upsert(data, *args, **kwargs):
        raise RuntimeError("PGRST204: schema cache error")

    client_mock.table("student_profiles").upsert = simulated_upsert
    try:
        with pytest.raises(supabase_repository.SupabaseRepositoryError):
            supabase_repository.upsert_student_profile({
                "user_id": "usr-pgrst-test",
                "target_role": "DevOps Engineer",
            })
    finally:
        client_mock.table("student_profiles").upsert = original_upsert
