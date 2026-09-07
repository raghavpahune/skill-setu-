import pytest
from starlette.testclient import TestClient

from app.main import app
from app.config import settings
from app.db import init_demo_users, _cache, get_user_by_email, save_user
from app.repositories.supabase_repository import get_client


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_demo_auth_roles_when_use_demo_data_is_false(client, monkeypatch):
    monkeypatch.setattr(settings, "use_demo_data", False)
    monkeypatch.setattr(settings, "demo_auth_enabled", True)
    init_demo_users()

    roles_to_test = [
        ("student@skillsetu.gov.in", "Password@123", "STUDENT"),
        ("employer@skillsetu.gov.in", "Password@123", "EMPLOYER"),
        ("institute@skillsetu.gov.in", "Password@123", "INSTITUTE"),
        ("government@skillsetu.gov.in", "Password@123", "GOVERNMENT"),
        ("admin@skillsetu.gov.in", "AdminPass@2026", "ADMIN"),
    ]

    for email, password, expected_role in roles_to_test:
        resp = client.post("/api/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "access_token" in data
        assert data["user"]["role"] == expected_role


def test_admin_login_with_invalid_credentials_fails(client, monkeypatch):
    monkeypatch.setattr(settings, "use_demo_data", False)
    monkeypatch.setattr(settings, "demo_auth_enabled", True)
    init_demo_users()

    resp = client.post("/api/auth/login", json={"email": "admin@skillsetu.gov.in", "password": "InvalidPassword@2026"})
    assert resp.status_code == 401
    assert "Invalid email or password" in resp.json()["detail"]


def test_get_user_by_email_queries_supabase_when_missing_from_cache(monkeypatch):
    mock_user = {
        "id": "usr-remote-999",
        "name": "Remote Database User",
        "email": "remote.user@skillsetu.gov.in",
        "role": "STUDENT",
    }
    client_db = get_client()
    client_db.table("users").rows.append(mock_user)

    _cache["users"] = [u for u in _cache.get("users", []) if u.get("email") != "remote.user@skillsetu.gov.in"]

    fetched = get_user_by_email("remote.user@skillsetu.gov.in")
    assert fetched is not None
    assert fetched["id"] == "usr-remote-999"
    assert fetched["full_name"] == "Remote Database User"


def test_save_user_populates_both_name_and_full_name():
    payload = {
        "id": "usr-test-integrity-001",
        "email": "integrity.check@skillsetu.gov.in",
        "full_name": "Integrity Candidate",
        "role": "STUDENT",
    }
    saved = save_user(payload)
    assert saved["name"] == "Integrity Candidate"
    assert saved["full_name"] == "Integrity Candidate"


def test_init_demo_users_does_not_overwrite_existing_supabase_user():
    client_db = get_client()
    existing_user = {
        "id": "usr-admin-001",
        "name": "Original Real Admin",
        "email": "admin@skillsetu.gov.in",
        "role": "ADMIN",
    }
    client_db.table("users").rows = [existing_user]
    init_demo_users()
    matched = next((u for u in client_db.table("users").rows if u.get("id") == "usr-admin-001"), None)
    assert matched is not None
    assert matched["name"] == "Original Real Admin"


def test_init_demo_users_filters_colliding_accounts_from_cache():
    from app.db import _cache
    client_db = get_client()
    existing_user = {
        "id": "usr-real-student-999",
        "name": "Original Real Student",
        "email": "student@skillsetu.gov.in",
        "role": "STUDENT",
    }
    client_db.table("users").rows = [existing_user]
    _cache["users"] = []
    init_demo_users()
    cached_student = next((u for u in _cache["users"] if u.get("id") == "usr-student-001"), None)
    assert cached_student is None


def test_init_demo_users_filters_colliding_id_in_no_database_mode(monkeypatch):
    from app.db import _cache
    from app.config import settings
    monkeypatch.setattr("app.db.get_supabase_client", lambda: None)
    monkeypatch.setattr(settings, "use_demo_data", True)
    _cache["users"] = [
        {
            "id": "usr-student-001",
            "email": "custom.student@example.com",
            "name": "Custom Student",
            "role": "STUDENT",
        }
    ]
    init_demo_users()
    matches = [u for u in _cache["users"] if u.get("id") == "usr-student-001"]
    assert len(matches) == 1
    assert matches[0]["email"] == "custom.student@example.com"
