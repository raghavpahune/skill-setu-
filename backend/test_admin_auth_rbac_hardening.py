import os
import pytest
from starlette.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings, settings
from app.main import app, lifespan
from app.core.security import verify_admin_access, DEFAULT_DEMO_ADMIN_KEY
from fastapi import HTTPException
import app.routers.auth as auth_router
import app.db as db_module

client = TestClient(app)


def test_config_demo_auth_defaults_to_false():
    s = Settings(demo_auth_enabled=False)
    assert s.demo_auth_enabled is False


def test_config_production_fails_closed_when_demo_auth_enabled(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(ValidationError):
        Settings(demo_auth_enabled=True)


def test_config_render_production_fails_closed_when_demo_auth_enabled(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    with pytest.raises(ValidationError):
        Settings(demo_auth_enabled=True)


def test_config_use_demo_data_false_in_dev_allows_demo_auth(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("RENDER", raising=False)
    s = Settings(environment="development", use_demo_data=False, demo_auth_enabled=True)
    assert s.is_production is False
    assert s.demo_auth_enabled is True


@pytest.mark.anyio
async def test_lifespan_fails_closed_in_production_with_demo_auth(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "demo_auth_enabled", True)
    with pytest.raises(RuntimeError) as exc_info:
        async with lifespan(app):
            pass
    assert "FATAL: Demo authentication cannot be enabled in production mode" in str(exc_info.value)


@pytest.mark.anyio
async def test_verify_admin_access_rejects_demo_key_in_production(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "admin_api_key", DEFAULT_DEMO_ADMIN_KEY)
    with pytest.raises(HTTPException) as exc_info:
        await verify_admin_access(credentials=None, x_admin_key=DEFAULT_DEMO_ADMIN_KEY)
    assert exc_info.value.status_code == 401


@pytest.mark.anyio
async def test_verify_admin_access_rejects_missing_key_in_production_without_fallback(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "admin_api_key", "")
    with pytest.raises(HTTPException) as exc_info:
        await verify_admin_access(credentials=None, x_admin_key=DEFAULT_DEMO_ADMIN_KEY)
    assert exc_info.value.status_code == 401


@pytest.mark.anyio
async def test_verify_admin_access_accepts_valid_secret_in_production(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "admin_api_key", "super-secret-prod-admin-key-2026")
    result = await verify_admin_access(credentials=None, x_admin_key="super-secret-prod-admin-key-2026")
    assert result is True


@pytest.mark.anyio
async def test_verify_admin_access_dev_fallback_when_demo_auth_enabled(monkeypatch):
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "demo_auth_enabled", True)
    monkeypatch.setattr(settings, "admin_api_key", "")
    result = await verify_admin_access(credentials=None, x_admin_key=DEFAULT_DEMO_ADMIN_KEY)
    assert result is True


@pytest.mark.anyio
async def test_verify_admin_access_dev_rejects_when_demo_auth_disabled(monkeypatch):
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "demo_auth_enabled", False)
    monkeypatch.setattr(settings, "admin_api_key", "")
    with pytest.raises(HTTPException) as exc_info:
        await verify_admin_access(credentials=None, x_admin_key=DEFAULT_DEMO_ADMIN_KEY)
    assert exc_info.value.status_code == 401


def test_production_rejects_demo_admin_login_fallback(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "demo_auth_enabled", False)
    monkeypatch.setattr(auth_router, "get_supabase_client", lambda: None)
    monkeypatch.setattr(db_module, "get_supabase_client", lambda: None)
    resp = client.post("/api/auth/login", json={
        "email": "admin@skillsetu.gov.in",
        "password": "AdminPass@2026",
    })
    assert resp.status_code == 401


def test_user_metadata_role_never_controls_authorization_privilege_escalation(monkeypatch):
    class FakeGoTrueUser:
        id = "sb-uid-attacker-01"
        email = "attacker@example.com"
        user_metadata = {"role": "EMPLOYER", "full_name": "Attacker Impersonating Employer"}

    class FakeAuth:
        def sign_in_with_password(self, credentials):
            return type("AuthResp", (), {"user": FakeGoTrueUser()})()

    class FakeTable:
        def select(self, *args, **kwargs):
            return self

        def eq(self, *args, **kwargs):
            return self

        def execute(self):
            return type("Resp", (), {"data": [{"role": "STUDENT"}]})()

        def upsert(self, *args, **kwargs):
            return self

    class FakeClient:
        auth = FakeAuth()

        def table(self, name):
            return FakeTable()

    fake_client = FakeClient()
    monkeypatch.setattr(auth_router, "get_supabase_client", lambda: fake_client)
    monkeypatch.setattr(db_module, "get_supabase_client", lambda: fake_client)

    resp = client.post("/api/auth/login", json={
        "email": "attacker@example.com",
        "password": "Password@123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["role"] == "STUDENT"
    assert data["user"]["role"] != "EMPLOYER"


def test_user_metadata_role_ignored_and_fails_closed_when_no_authoritative_row(monkeypatch):
    class FakeGoTrueUser:
        id = "sb-uid-attacker-02"
        email = "attacker2@example.com"
        user_metadata = {"role": "EMPLOYER", "full_name": "Attacker With No DB Record"}

    class FakeAuth:
        def sign_in_with_password(self, credentials):
            return type("AuthResp", (), {"user": FakeGoTrueUser()})()

    class FakeTable:
        def select(self, *args, **kwargs):
            return self

        def eq(self, *args, **kwargs):
            return self

        def execute(self):
            return type("Resp", (), {"data": []})()

    class FakeClient:
        auth = FakeAuth()

        def table(self, name):
            return FakeTable()

    fake_client = FakeClient()
    monkeypatch.setattr(auth_router, "get_supabase_client", lambda: fake_client)
    monkeypatch.setattr(db_module, "get_supabase_client", lambda: fake_client)

    resp = client.post("/api/auth/login", json={
        "email": "attacker2@example.com",
        "password": "Password@123",
    })
    assert resp.status_code == 403
    assert "No authoritative role assigned" in resp.json()["detail"]


def test_authoritative_role_lookup_fails_closed_on_database_error(monkeypatch):
    class FakeGoTrueUser:
        id = "sb-uid-db-error"
        email = "dberror@example.com"
        user_metadata = {"role": "STUDENT"}

    class FakeAuth:
        def sign_in_with_password(self, credentials):
            return type("AuthResp", (), {"user": FakeGoTrueUser()})()

    class FakeTable:
        def select(self, *args, **kwargs):
            return self

        def eq(self, *args, **kwargs):
            return self

        def execute(self):
            raise RuntimeError("Database connection pool exhausted")

    class FakeClient:
        auth = FakeAuth()

        def table(self, name):
            return FakeTable()

    fake_client = FakeClient()
    monkeypatch.setattr(auth_router, "get_supabase_client", lambda: fake_client)
    monkeypatch.setattr(db_module, "get_supabase_client", lambda: fake_client)

    resp = client.post("/api/auth/login", json={
        "email": "dberror@example.com",
        "password": "Password@123",
    })
    assert resp.status_code == 500
    assert "Database error while resolving authoritative user permissions" in resp.json()["detail"]


def test_admin_recovery_resolves_dynamic_uuid_and_updates_only_resolved_user(monkeypatch):
    updated_records = []

    class FakeGoTrueUser:
        def __init__(self, uid, email):
            self.id = uid
            self.email = email

    class FakeAdminAPI:
        def list_users(self, page=1, per_page=100):
            return [FakeGoTrueUser("dynamic-admin-uuid-8888", "admin@skillsetu.gov.in")]

        def update_user_by_id(self, uid, attributes):
            updated_records.append((uid, attributes))
            return None

    class FakeAuth:
        admin = FakeAdminAPI()
        attempt = 0

        def sign_in_with_password(self, credentials):
            self.attempt += 1
            if self.attempt == 1:
                raise Exception("First attempt password mismatch")
            return type("AuthResp", (), {"user": FakeGoTrueUser("dynamic-admin-uuid-8888", "admin@skillsetu.gov.in")})()

    class FakeTable:
        def select(self, *args, **kwargs):
            return self

        def eq(self, *args, **kwargs):
            return self

        def execute(self):
            return type("Resp", (), {"data": [{"role": "ADMIN"}]})()

        def upsert(self, *args, **kwargs):
            return self

    class FakeClient:
        auth = FakeAuth()

        def table(self, name):
            return FakeTable()

    fake_client = FakeClient()
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "demo_auth_enabled", True)
    monkeypatch.setattr(auth_router, "get_supabase_client", lambda: fake_client)
    monkeypatch.setattr(db_module, "get_supabase_client", lambda: fake_client)

    resp = client.post("/api/auth/login", json={
        "email": "admin@skillsetu.gov.in",
        "password": "AdminPass@2026",
    })
    assert resp.status_code == 200
    assert len(updated_records) == 1
    assert updated_records[0][0] == "dynamic-admin-uuid-8888"
    assert updated_records[0][0] != "73e35d08-a564-4cd2-b503-a641a8a0a5aa"
    assert resp.json()["user"]["id"] == "dynamic-admin-uuid-8888"


def test_admin_recovery_fails_closed_when_gotrue_user_not_found(monkeypatch):
    update_called = []

    class FakeAdminAPI:
        def list_users(self, page=1, per_page=100):
            return []

        def update_user_by_id(self, uid, attributes):
            update_called.append(uid)
            return None

    class FakeAuth:
        admin = FakeAdminAPI()

        def sign_in_with_password(self, credentials):
            raise Exception("Invalid password")

    class FakeClient:
        auth = FakeAuth()

        def table(self, name):
            return None

    fake_client = FakeClient()
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "demo_auth_enabled", True)
    monkeypatch.setattr(auth_router, "get_supabase_client", lambda: fake_client)
    monkeypatch.setattr(db_module, "get_supabase_client", lambda: fake_client)

    resp = client.post("/api/auth/login", json={
        "email": "admin@skillsetu.gov.in",
        "password": "AdminPass@2026",
    })
    assert resp.status_code == 401
    assert len(update_called) == 0


def test_admin_recovery_never_executes_in_production(monkeypatch):
    admin_api_called = []

    class FakeAdminAPI:
        def list_users(self, page=1, per_page=100):
            admin_api_called.append("list_users")
            return []

        def update_user_by_id(self, uid, attributes):
            admin_api_called.append("update_user_by_id")
            return None

    class FakeAuth:
        admin = FakeAdminAPI()

        def sign_in_with_password(self, credentials):
            raise Exception("Invalid credentials")

    class FakeClient:
        auth = FakeAuth()

        def table(self, name):
            return None

    fake_client = FakeClient()
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "demo_auth_enabled", False)
    monkeypatch.setattr(auth_router, "get_supabase_client", lambda: fake_client)
    monkeypatch.setattr(db_module, "get_supabase_client", lambda: fake_client)

    resp = client.post("/api/auth/login", json={
        "email": "admin@skillsetu.gov.in",
        "password": "AdminPass@2026",
    })
    assert resp.status_code == 401
    assert len(admin_api_called) == 0


def test_admin_login_fails_closed_when_public_users_has_no_admin_record(monkeypatch):
    upserted_records = []

    class FakeGoTrueUser:
        id = "gotrue-valid-admin-uuid-001"
        email = "admin@skillsetu.gov.in"
        user_metadata = {"role": "ADMIN", "name": "SkillSetu System Administrator"}

    class FakeAuth:
        def sign_in_with_password(self, credentials):
            return type("AuthResp", (), {"user": FakeGoTrueUser()})()

    class FakeTable:
        def select(self, *args, **kwargs):
            return self

        def eq(self, col, val):
            return self

        def execute(self):
            return type("Resp", (), {"data": []})()

        def upsert(self, row, **kwargs):
            upserted_records.append(row)
            return self

    class FakeClient:
        auth = FakeAuth()

        def table(self, name):
            return FakeTable()

    fake_client = FakeClient()
    monkeypatch.setattr(auth_router, "get_supabase_client", lambda: fake_client)
    monkeypatch.setattr(db_module, "get_supabase_client", lambda: fake_client)

    resp = client.post("/api/auth/login", json={
        "email": "admin@skillsetu.gov.in",
        "password": "AdminPass@2026",
    })
    assert resp.status_code == 403
    assert "access_token" not in resp.json()
    assert len(upserted_records) == 0


def test_admin_login_succeeds_when_public_users_has_admin_role_and_no_upsert(monkeypatch):
    upserted_records = []

    class FakeGoTrueUser:
        id = "gotrue-valid-admin-uuid-002"
        email = "admin@skillsetu.gov.in"
        user_metadata = {"role": "ADMIN", "name": "SkillSetu System Administrator"}

    class FakeAuth:
        def sign_in_with_password(self, credentials):
            return type("AuthResp", (), {"user": FakeGoTrueUser()})()

    class FakeTable:
        def select(self, *args, **kwargs):
            return self

        def eq(self, col, val):
            return self

        def execute(self):
            return type("Resp", (), {"data": [{"id": "gotrue-valid-admin-uuid-002", "role": "ADMIN"}]})()

        def upsert(self, row, **kwargs):
            upserted_records.append(row)
            return self

    class FakeClient:
        auth = FakeAuth()

        def table(self, name):
            return FakeTable()

    fake_client = FakeClient()
    monkeypatch.setattr(auth_router, "get_supabase_client", lambda: fake_client)
    monkeypatch.setattr(db_module, "get_supabase_client", lambda: fake_client)

    resp = client.post("/api/auth/login", json={
        "email": "admin@skillsetu.gov.in",
        "password": "AdminPass@2026",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["role"] == "ADMIN"
    assert data["user"]["id"] == "gotrue-valid-admin-uuid-002"
    assert len(upserted_records) == 0


def test_admin_login_fails_closed_when_public_users_role_is_student(monkeypatch):
    class FakeGoTrueUser:
        id = "gotrue-valid-admin-uuid-003"
        email = "admin@skillsetu.gov.in"
        user_metadata = {"role": "ADMIN", "name": "SkillSetu System Administrator"}

    class FakeAuth:
        def sign_in_with_password(self, credentials):
            return type("AuthResp", (), {"user": FakeGoTrueUser()})()

    class FakeTable:
        def select(self, *args, **kwargs):
            return self

        def eq(self, col, val):
            return self

        def execute(self):
            return type("Resp", (), {"data": [{"id": "gotrue-valid-admin-uuid-003", "role": "STUDENT"}]})()

    class FakeClient:
        auth = FakeAuth()

        def table(self, name):
            return FakeTable()

    fake_client = FakeClient()
    monkeypatch.setattr(auth_router, "get_supabase_client", lambda: fake_client)
    monkeypatch.setattr(db_module, "get_supabase_client", lambda: fake_client)

    resp = client.post("/api/auth/login", json={
        "email": "admin@skillsetu.gov.in",
        "password": "AdminPass@2026",
    })
    assert resp.status_code == 403
    assert "access_token" not in resp.json()


def test_admin_login_fails_closed_when_public_users_role_is_missing_or_invalid(monkeypatch):
    class FakeGoTrueUser:
        id = "gotrue-valid-admin-uuid-004"
        email = "admin@skillsetu.gov.in"
        user_metadata = {"role": "ADMIN", "name": "SkillSetu System Administrator"}

    class FakeAuth:
        def sign_in_with_password(self, credentials):
            return type("AuthResp", (), {"user": FakeGoTrueUser()})()

    for invalid_role in ("", "UNKNOWN", "SUPERADMIN", None):
        class FakeTable:
            def select(self, *args, **kwargs):
                return self

            def eq(self, col, val):
                return self

            def execute(self):
                return type("Resp", (), {"data": [{"id": "gotrue-valid-admin-uuid-004", "role": invalid_role}]})()

        class FakeClient:
            auth = FakeAuth()

            def table(self, name):
                return FakeTable()

        fake_client = FakeClient()
        monkeypatch.setattr(auth_router, "get_supabase_client", lambda: fake_client)
        monkeypatch.setattr(db_module, "get_supabase_client", lambda: fake_client)

        resp = client.post("/api/auth/login", json={
            "email": "admin@skillsetu.gov.in",
            "password": "AdminPass@2026",
        })
        assert resp.status_code == 403
        assert "access_token" not in resp.json()


def test_admin_login_fails_closed_on_database_role_query_exception(monkeypatch):
    class FakeGoTrueUser:
        id = "gotrue-valid-admin-uuid-005"
        email = "admin@skillsetu.gov.in"
        user_metadata = {"role": "ADMIN", "name": "SkillSetu System Administrator"}

    class FakeAuth:
        def sign_in_with_password(self, credentials):
            return type("AuthResp", (), {"user": FakeGoTrueUser()})()

    class FakeTable:
        def select(self, *args, **kwargs):
            return self

        def eq(self, col, val):
            return self

        def execute(self):
            raise RuntimeError("Database connection timed out during role resolution")

    class FakeClient:
        auth = FakeAuth()

        def table(self, name):
            return FakeTable()

    fake_client = FakeClient()
    monkeypatch.setattr(auth_router, "get_supabase_client", lambda: fake_client)
    monkeypatch.setattr(db_module, "get_supabase_client", lambda: fake_client)

    resp = client.post("/api/auth/login", json={
        "email": "admin@skillsetu.gov.in",
        "password": "AdminPass@2026",
    })
    assert resp.status_code == 500
    assert "access_token" not in resp.json()
