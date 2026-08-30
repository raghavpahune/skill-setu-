"""Test suite for Phase 23: Real Authentication + Role-Based Access Control (RBAC)."""
from datetime import timedelta
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.db import init_db, save_user, save_student_assessment
from app.core.security import hash_password, create_access_token

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    from app.db import _cache
    if "users" in _cache:
        _cache["users"] = [
            u for u in _cache["users"]
            if not any(k in u.get("email", "") for k in ("test@", ".test", "isolated@", "dup.test", "newstudent", "fakeadmin"))
        ]



# ---------------------------------------------------------------------------
# 1. Registration Tests
# ---------------------------------------------------------------------------

def test_register_student_success():
    """POST /api/auth/register successfully registers a new student."""
    payload = {
        "email": "newstudent.test@skillsetu.gov.in",
        "password": "SecurePassword123",
        "full_name": "Rohan Deshmukh",
        "role": "STUDENT",
        "district": "Pune",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "success"
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "newstudent.test@skillsetu.gov.in"
    assert data["user"]["role"] == "STUDENT"
    assert "hashed_password" not in data["user"]


def test_register_duplicate_email_conflict():
    """POST /api/auth/register rejects already registered email with 409 Conflict."""
    payload = {
        "email": "dup.test@skillsetu.gov.in",
        "password": "SecurePassword123",
        "full_name": "Test User",
        "role": "STUDENT",
    }
    res1 = client.post("/api/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/auth/register", json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


def test_register_public_admin_blocked():
    """POST /api/auth/register rejects public attempt to register as ADMIN."""
    payload = {
        "email": "fakeadmin@skillsetu.gov.in",
        "password": "SecurePassword123",
        "full_name": "Malicious Admin",
        "role": "ADMIN",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 422


def test_register_invalid_role():
    """POST /api/auth/register rejects unsupported role."""
    payload = {
        "email": "invalidrole@skillsetu.gov.in",
        "password": "SecurePassword123",
        "full_name": "Invalid Role",
        "role": "SUPERUSER",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 422


def test_register_weak_password():
    """POST /api/auth/register rejects password shorter than 6 characters."""
    payload = {
        "email": "weakpass@skillsetu.gov.in",
        "password": "123",
        "full_name": "Short Pass",
        "role": "STUDENT",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# 2. Login Tests
# ---------------------------------------------------------------------------

def test_login_demo_accounts_success():
    """POST /api/auth/login succeeds with demo credentials for each role."""
    roles_credentials = [
        ("student@skillsetu.gov.in", "Password@123", "STUDENT"),
        ("employer@skillsetu.gov.in", "Password@123", "EMPLOYER"),
        ("institute@skillsetu.gov.in", "Password@123", "INSTITUTE"),
        ("government@skillsetu.gov.in", "Password@123", "GOVERNMENT"),
        ("admin@skillsetu.gov.in", "AdminPass@2026", "ADMIN"),
    ]
    for email, password, expected_role in roles_credentials:
        res = client.post("/api/auth/login", json={"email": email, "password": password})
        assert res.status_code == 200, f"Login failed for {email}"
        data = res.json()
        assert "access_token" in data
        assert data["user"]["role"] == expected_role


def test_login_wrong_password():
    """POST /api/auth/login rejects incorrect password with 401."""
    res = client.post("/api/auth/login", json={
        "email": "student@skillsetu.gov.in",
        "password": "WrongPassword999",
    })
    assert res.status_code == 401
    assert "Invalid email or password" in res.json()["detail"]


def test_login_unknown_user():
    """POST /api/auth/login rejects unregistered email with 401."""
    res = client.post("/api/auth/login", json={
        "email": "nonexistent.user.999@skillsetu.gov.in",
        "password": "Password@123",
    })
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# 3. /api/auth/me & Token Validation Tests
# ---------------------------------------------------------------------------

def test_get_me_with_valid_token():
    """GET /api/auth/me returns the profile of the authenticated user."""
    login_res = client.post("/api/auth/login", json={
        "email": "student@skillsetu.gov.in",
        "password": "Password@123",
    })
    token = login_res.json()["access_token"]

    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    user_data = me_res.json()["user"]
    assert user_data["email"] == "student@skillsetu.gov.in"
    assert user_data["role"] == "STUDENT"
    assert "hashed_password" not in user_data


def test_get_me_missing_token():
    """GET /api/auth/me without token returns 401 Unauthorized."""
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_get_me_expired_token():
    """GET /api/auth/me with expired token returns 401 Unauthorized."""
    expired_token = create_access_token(
        {"sub": "usr-student-001", "email": "student@skillsetu.gov.in", "role": "STUDENT"},
        expires_delta=timedelta(seconds=-10),
    )
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401
    assert "Invalid or expired" in res.json()["detail"]


# ---------------------------------------------------------------------------
# 4. Role-Based Access Control (RBAC) Matrix Tests
# ---------------------------------------------------------------------------

def test_rbac_admin_endpoint_access_matrix():
    """Admin endpoints reject non-admin tokens with 403 Forbidden, allow admin token with 200 OK."""
    # Obtain tokens for all roles
    tokens = {}
    for role_email, passw in [
        ("STUDENT", ("student@skillsetu.gov.in", "Password@123")),
        ("EMPLOYER", ("employer@skillsetu.gov.in", "Password@123")),
        ("INSTITUTE", ("institute@skillsetu.gov.in", "Password@123")),
        ("GOVERNMENT", ("government@skillsetu.gov.in", "Password@123")),
        ("ADMIN", ("admin@skillsetu.gov.in", "AdminPass@2026")),
    ]:
        login_res = client.post("/api/auth/login", json={"email": passw[0], "password": passw[1]})
        tokens[role_email] = login_res.json()["access_token"]

    admin_endpoints = [
        "/api/admin/assessments",
        "/api/admin/employer/demands",
        "/api/admin/gov/opportunities",
        "/api/admin/assessments/stats/summary",
    ]

    # Non-admin roles MUST receive 403 Forbidden
    for non_admin_role in ["STUDENT", "EMPLOYER", "INSTITUTE", "GOVERNMENT"]:
        token = tokens[non_admin_role]
        for ep in admin_endpoints:
            res = client.get(ep, headers={"Authorization": f"Bearer {token}"})
            assert res.status_code == 403, f"Expected 403 for {non_admin_role} on {ep}, got {res.status_code}"

    # ADMIN token MUST succeed with 200 OK
    admin_token = tokens["ADMIN"]
    for ep in admin_endpoints:
        res = client.get(ep, headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200, f"Expected 200 for ADMIN on {ep}, got {res.status_code}"


def test_anonymous_admin_access_rejected():
    """Admin endpoints reject anonymous requests without credentials with 401 Unauthorized."""
    assert client.get("/api/admin/assessments").status_code == 401
    assert client.get("/api/admin/employer/demands").status_code == 401
    assert client.get("/api/admin/gov/opportunities").status_code == 401


# ---------------------------------------------------------------------------
# 5. User Ownership & Data Isolation Tests
# ---------------------------------------------------------------------------

def test_student_data_isolation():
    """A student cannot access another student's private assessment record."""
    # Create assessment owned by student 1
    ast_1 = {
        "id": "ast-private-user-1",
        "user_id": "usr-student-001",
        "name": "Student One",
        "career_goal": "AI Engineer",
        "current_skills": [],
        "quiz_score_pct": 80,
        "skill_match_pct": 70,
        "combined_readiness_score": 75,
        "source": "USER_SUBMITTED",
        "is_demo": False,
    }
    save_student_assessment(ast_1)

    # Register student 2
    reg_2 = client.post("/api/auth/register", json={
        "email": "student2.isolated@skillsetu.gov.in",
        "password": "Password@123",
        "full_name": "Student Two",
        "role": "STUDENT",
    })
    token_2 = reg_2.json()["access_token"]

    # Student 2 attempting to view Student 1's private record -> 403 Forbidden
    res_forbidden = client.get(
        "/api/student/assessment/ast-private-user-1",
        headers={"Authorization": f"Bearer {token_2}"},
    )
    assert res_forbidden.status_code == 403

    # Student 1 accessing their own record -> 200 OK
    token_1 = client.post("/api/auth/login", json={
        "email": "student@skillsetu.gov.in",
        "password": "Password@123",
    }).json()["access_token"]
    res_owner = client.get(
        "/api/student/assessment/ast-private-user-1",
        headers={"Authorization": f"Bearer {token_1}"},
    )
    assert res_owner.status_code == 200

    # Admin accessing Student 1's record -> 200 OK
    token_admin = client.post("/api/auth/login", json={
        "email": "admin@skillsetu.gov.in",
        "password": "AdminPass@2026",
    }).json()["access_token"]
    res_admin = client.get(
        "/api/student/assessment/ast-private-user-1",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert res_admin.status_code == 200
