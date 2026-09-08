import uuid
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.config import settings
from app.db import init_demo_users, _cache, get_user_by_email, get_user_by_id


@pytest.fixture
def test_client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def isolate_users_cache():
    from pathlib import Path
    from app.db import _save_user_lock
    initial = [dict(u) for u in _cache.get("users", [])]
    runtime_path = Path(__file__).resolve().parent.parent / "data" / "real" / "users_runtime.json"
    initial_file = runtime_path.read_text(encoding="utf-8") if runtime_path.exists() else None
    yield
    with _save_user_lock:
        if "users" in _cache:
            _cache["users"] = initial
        if initial_file is not None:
            runtime_path.write_text(initial_file, encoding="utf-8")
        elif runtime_path.exists():
            runtime_path.unlink()


def test_auth_all_five_roles_and_admin_uid(test_client, monkeypatch):
    monkeypatch.setattr(settings, "use_demo_data", False)
    monkeypatch.setattr(settings, "demo_auth_enabled", True)
    init_demo_users()

    roles = [
        ("student@skillsetu.gov.in", "Password@123", "STUDENT"),
        ("employer@skillsetu.gov.in", "Password@123", "EMPLOYER"),
        ("institute@skillsetu.gov.in", "Password@123", "INSTITUTE"),
        ("government@skillsetu.gov.in", "Password@123", "GOVERNMENT"),
        ("admin@skillsetu.gov.in", "AdminPass@2026", "ADMIN"),
    ]

    for email, pwd, expected_role in roles:
        resp = test_client.post("/api/auth/login", json={"email": email, "password": pwd})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["user"]["role"] == expected_role
        assert "access_token" in body

    admin_user = get_user_by_email("admin@skillsetu.gov.in")
    assert admin_user is not None
    assert admin_user["id"] in ("73e35d08-a564-4cd2-b503-a641a8a0a5aa", "usr-admin-001")

    by_uid = get_user_by_id("73e35d08-a564-4cd2-b503-a641a8a0a5aa")
    assert by_uid is not None
    assert by_uid["email"] == "admin@skillsetu.gov.in"

    by_legacy = get_user_by_id("usr-admin-001")
    assert by_legacy is not None
    assert by_legacy["email"] == "admin@skillsetu.gov.in"


def test_student_profile_skill_passport_persistence(test_client):
    unique_email = f"market.student.{uuid.uuid4().hex[:8]}@skillsetu.gov.in"
    reg_resp = test_client.post("/api/auth/register", json={
        "email": unique_email,
        "password": "Password@123",
        "full_name": "Market Verification Student",
        "role": "STUDENT",
    })
    assert reg_resp.status_code == 201
    token = reg_resp.json()["access_token"]
    student_id = reg_resp.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "full_name": "Market Verification Student",
        "institution": "Government College of Engineering Pune",
        "degree": "B.Tech Computer Science",
        "education_level": "Undergraduate (B.Tech / B.E / B.Sc)",
        "academic_year": "Final Year",
        "graduation_year": 2026,
        "desired_role": "AI Engineer",
        "target_role": "AI Engineer",
        "preferred_location": "Pune",
        "career_interests": ["Machine Learning", "Cloud Systems"],
        "skills": [
            {"skill_name": "Python", "proficiency": "advanced"},
            {"skill_name": "FastAPI", "proficiency": "intermediate"},
            {"skill_name": "Docker", "proficiency": "beginner"},
        ],
        "projects": [
            {
                "name": "SkillSetu Intelligence",
                "description": "Labour market curriculum intelligence system",
                "skills": ["Python", "FastAPI"],
                "url": "https://github.com/skillsetu/demo",
            }
        ],
        "certifications": [
            {
                "name": "Cloud Practitioner",
                "issuer": "AWS",
                "issue_date": "2026-01-10",
                "url": "https://aws.cert/123",
            }
        ],
        "courses": [
            {
                "course_name": "Deep Learning Specialization",
                "provider": "DeepLearning.AI",
                "status": "completed",
            }
        ],
    }

    create_resp = test_client.post("/api/student/profile", json=payload, headers=headers)
    assert create_resp.status_code in (200, 201)
    created_data = create_resp.json()
    assert created_data["status"] == "success"
    assert created_data["profile"]["user_id"] == student_id
    assert created_data["profile"]["institution"] == "Government College of Engineering Pune"

    get_resp = test_client.get("/api/student/profile", headers=headers)
    assert get_resp.status_code == 200
    retrieved = get_resp.json()["profile"]
    assert retrieved["user_id"] == student_id
    assert retrieved["degree"] == "B.Tech Computer Science"
    assert len(retrieved["skills"]) >= 3


def test_employee_profile_persistence(test_client):
    unique_email = f"market.emp.{uuid.uuid4().hex[:8]}@skillsetu.gov.in"
    reg_resp = test_client.post("/api/auth/register", json={
        "email": unique_email,
        "password": "Password@123",
        "full_name": "Market Verification Professional",
        "role": "EMPLOYEE",
    })
    assert reg_resp.status_code == 201
    token = reg_resp.json()["access_token"]
    emp_id = reg_resp.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "full_name": "Market Verification Professional",
        "current_role": "Junior Backend Developer",
        "years_of_experience": 2,
        "industry": "Information Technology",
        "education": "B.Sc Computer Science",
        "target_role": "Senior Backend Architect",
        "preferred_location": "Mumbai",
        "skills": [
            {"skill_name": "Python", "proficiency": "advanced"},
            {"skill_name": "PostgreSQL", "proficiency": "intermediate"},
        ],
        "certifications": [
            {
                "name": "Postgres Associate",
                "issuer": "PostgreSQL Foundation",
                "issue_date": "2025-06-15",
                "url": "https://pg.cert/456",
            }
        ],
    }

    create_resp = test_client.post("/api/employee/profile", json=payload, headers=headers)
    assert create_resp.status_code in (200, 201)
    body = create_resp.json()
    assert body["status"] == "success"
    assert body["profile"]["user_id"] == emp_id
    assert body["profile"]["current_role"] == "Junior Backend Developer"

    get_resp = test_client.get("/api/employee/profile", headers=headers)
    assert get_resp.status_code == 200
    retrieved = get_resp.json()["profile"]
    assert retrieved["user_id"] == emp_id
    assert retrieved["industry"] == "Information Technology"


def test_personalized_assessment_and_readiness_score(test_client):
    unique_email = f"assessment.student.{uuid.uuid4().hex[:8]}@skillsetu.gov.in"
    reg_resp = test_client.post("/api/auth/register", json={
        "email": unique_email,
        "password": "Password@123",
        "full_name": "Assessment Student",
        "role": "STUDENT",
    })
    assert reg_resp.status_code == 201
    token = reg_resp.json()["access_token"]
    student_id = reg_resp.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    profile_payload = {
        "full_name": "Assessment Student",
        "institution": "COEP Pune",
        "degree": "B.Tech Computer Science",
        "education_level": "Undergraduate (B.Tech / B.E / B.Sc)",
        "academic_year": "Final Year",
        "graduation_year": 2026,
        "desired_role": "Software Engineer",
        "target_role": "Software Engineer",
        "preferred_location": "Pune",
        "career_interests": ["Web Development", "Databases"],
        "skills": [
            {"skill_name": "Python", "proficiency": "advanced"},
            {"skill_name": "SQL", "proficiency": "intermediate"},
        ],
        "projects": [],
        "certifications": [],
        "courses": [],
    }
    profile_resp = test_client.post("/api/student/profile", json=profile_payload, headers=headers)
    assert profile_resp.status_code in (200, 201)

    questions_resp = test_client.get("/api/student/assessment/quiz-questions", headers=headers)
    assert questions_resp.status_code == 200
    q_data = questions_resp.json()
    assert "questions" in q_data
    questions = q_data["questions"]
    assert len(questions) > 0

    answers = {
        str(q["id"]): (q["options"][0]["key"] if isinstance(q["options"][0], dict) else str(q["options"][0]))
        for q in questions if "options" in q and q["options"]
    }

    submission_payload = {
        "name": "Assessment Student",
        "education": "B.Tech Computer Science",
        "district": "Pune",
        "career_goal": "Software Engineer",
        "interests": ["Algorithms", "Cloud Computing"],
        "current_skills": [
            {"skill_name": "Python", "proficiency": "advanced"},
            {"skill_name": "SQL", "proficiency": "intermediate"},
        ],
        "quiz_answers": answers,
    }

    submit_resp = test_client.post("/api/student/assessment", json=submission_payload, headers=headers)
    assert submit_resp.status_code == 200
    result = submit_resp.json()
    assert result["status"] == "success"
    assert "combined_readiness_score" in result["assessment"]
    assert 0 <= result["assessment"]["combined_readiness_score"] <= 100
    assert result["assessment"]["user_id"] == student_id


def test_adaptive_roadmap_recalculation(test_client):
    unique_email = f"roadmap.student.{uuid.uuid4().hex[:8]}@skillsetu.gov.in"
    reg_resp = test_client.post("/api/auth/register", json={
        "email": unique_email,
        "password": "Password@123",
        "full_name": "Roadmap Candidate",
        "role": "STUDENT",
    })
    assert reg_resp.status_code == 201
    token = reg_resp.json()["access_token"]
    student_id = reg_resp.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    profile_payload = {
        "full_name": "Roadmap Candidate",
        "institution": "VJTI Mumbai",
        "degree": "B.Tech IT",
        "education_level": "Undergraduate (B.Tech / B.E / B.Sc)",
        "academic_year": "3rd Year",
        "graduation_year": 2027,
        "desired_role": "DevOps Engineer",
        "target_role": "DevOps Engineer",
        "preferred_location": "Mumbai",
        "career_interests": ["DevOps", "Infrastructure"],
        "skills": [
            {"skill_name": "Linux", "proficiency": "advanced"},
            {"skill_name": "Git", "proficiency": "intermediate"},
        ],
        "projects": [],
        "certifications": [],
        "courses": [],
    }
    profile_resp = test_client.post("/api/student/profile", json=profile_payload, headers=headers)
    assert profile_resp.status_code in (200, 201)

    get_resp = test_client.get("/api/student/me/roadmap", headers=headers)
    assert get_resp.status_code == 200

    recalc_resp = test_client.post("/api/student/me/roadmap/recalculate", headers=headers)
    assert recalc_resp.status_code == 200
    roadmap_data = recalc_resp.json()
    assert "has_roadmap" in roadmap_data


def test_gov_opportunity_publish_persistence_and_reload(test_client):
    unique_email = f"gov.publisher.{uuid.uuid4().hex[:8]}@skillsetu.gov.in"
    reg_resp = test_client.post("/api/auth/register", json={
        "email": unique_email,
        "password": "Password@123",
        "full_name": "State Skill Officer",
        "role": "GOVERNMENT",
    })
    assert reg_resp.status_code == 201
    token = reg_resp.json()["access_token"]
    gov_headers = {"Authorization": f"Bearer {token}"}

    opp_payload = {
        "name": "State Green Hydrogen Apprenticeship",
        "department": "Energy & Skill Development",
        "description": "Apprenticeship programme for green hydrogen plant operators.",
        "eligibility_criteria": "ITI or Polytechnic Diploma holders",
        "target_skills": ["Hydrogen Safety", "Cryogenic Handling"],
        "district_coverage": ["Pune", "Nagpur"],
        "opportunity_type": "APPRENTICESHIP",
        "application_url": "https://mahaswayam.gov.in",
        "deadline": "2026-12-31",
        "status": "active",
    }

    pub_resp = test_client.post("/api/gov/opportunities", json=opp_payload, headers=gov_headers)
    assert pub_resp.status_code == 201
    created = pub_resp.json()["opportunity"]
    assert created["name"] == "State Green Hydrogen Apprenticeship"
    assert created["department"] == "Energy & Skill Development"
    opp_id = created["id"]

    list_resp = test_client.get("/api/gov/opportunities")
    assert list_resp.status_code == 200
    opps = list_resp.json() if isinstance(list_resp.json(), list) else list_resp.json().get("opportunities", [])
    matching = [o for o in opps if o.get("id") == opp_id]
    assert len(matching) == 1
    assert matching[0]["name"] == "State Green Hydrogen Apprenticeship"

    detail_resp = test_client.get(f"/api/gov/opportunities/{opp_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["name"] == "State Green Hydrogen Apprenticeship"


def test_gov_opportunity_rbac_protection(test_client):
    unique_email = f"student.unauth.{uuid.uuid4().hex[:8]}@skillsetu.gov.in"
    reg_resp = test_client.post("/api/auth/register", json={
        "email": unique_email,
        "password": "Password@123",
        "full_name": "Regular Student",
        "role": "STUDENT",
    })
    assert reg_resp.status_code == 201
    token = reg_resp.json()["access_token"]
    student_headers = {"Authorization": f"Bearer {token}"}

    opp_payload = {
        "name": "Unauthorized Scheme",
        "department": "Fake Dept",
        "description": "Should fail with 403 Forbidden.",
    }
    unauth_resp = test_client.post("/api/gov/opportunities", json=opp_payload, headers=student_headers)
    assert unauth_resp.status_code == 403

    no_auth_resp = test_client.post("/api/gov/opportunities", json=opp_payload)
    assert no_auth_resp.status_code == 401


def test_auth_save_user_failure_fails_closed(test_client, monkeypatch):
    import app.routers.auth as auth_router

    class FakeUser:
        id = "sb-user-timeout-test"
        user_metadata = {"role": "STUDENT", "name": "Timeout User"}

    class FakeAuthResp:
        user = FakeUser()

    class FakeAuth:
        def sign_in_with_password(self, credentials):
            return FakeAuthResp()

    class FakeClient:
        auth = FakeAuth()

        def table(self, name):
            class FakeQuery:
                def select(self, *args, **kwargs):
                    return self

                def eq(self, *args, **kwargs):
                    return self

                def execute(self):
                    return type("Resp", (), {"data": [{"role": "STUDENT"}]})()

            return FakeQuery()

    monkeypatch.setattr(auth_router, "get_supabase_client", lambda: FakeClient())

    def failing_save_user(user):
        raise TimeoutError("Persistence timed out")

    monkeypatch.setattr(auth_router, "save_user", failing_save_user)

    resp = test_client.post("/api/auth/login", json={
        "email": "timeout.user@example.com",
        "password": "Password@123",
    })
    assert resp.status_code == 500
    assert "access_token" not in resp.json()


def test_admin_login_with_intended_credentials_and_role_resolution(test_client):
    from app.db import init_demo_users
    init_demo_users()
    resp = test_client.post("/api/auth/login", json={
        "email": "admin@skillsetu.gov.in",
        "password": "AdminPass@2026",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "access_token" in data
    assert data["user"]["role"] == "ADMIN"
    assert data["user"]["id"] == "73e35d08-a564-4cd2-b503-a641a8a0a5aa"
    token = data["access_token"]
    admin_headers = {"Authorization": f"Bearer {token}"}
    gov_resp = test_client.get("/api/admin/data-governance", headers=admin_headers)
    assert gov_resp.status_code == 200


def test_admin_account_reconciliation_when_preloaded_without_password(test_client):
    from app.db import _cache, init_demo_users
    _cache["users"] = [
        {
            "id": "73e35d08-a564-4cd2-b503-a641a8a0a5aa",
            "email": "admin@skillsetu.gov.in",
            "name": "SkillSetu System Administrator",
            "role": "ADMIN",
        }
    ]
    init_demo_users()
    resp = test_client.post("/api/auth/login", json={
        "email": "admin@skillsetu.gov.in",
        "password": "AdminPass@2026",
    })
    assert resp.status_code == 200
    user = resp.json()["user"]
    assert user["role"] == "ADMIN"
    assert user["id"] == "73e35d08-a564-4cd2-b503-a641a8a0a5aa"


def test_admin_invalid_password_and_nonexistent_fails(test_client):
    from app.db import init_demo_users
    init_demo_users()
    resp = test_client.post("/api/auth/login", json={
        "email": "admin@skillsetu.gov.in",
        "password": "WrongPassword@999",
    })
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password"

    resp_nonexistent = test_client.post("/api/auth/login", json={
        "email": "nonexistent.admin@skillsetu.gov.in",
        "password": "AdminPass@2026",
    })
    assert resp_nonexistent.status_code == 401


def test_admin_role_cannot_be_self_assigned_during_registration(test_client):
    resp = test_client.post("/api/auth/register", json={
        "email": f"malicious.admin.{uuid.uuid4().hex[:8]}@skillsetu.gov.in",
        "password": "Password@123",
        "full_name": "Attacker Admin",
        "role": "ADMIN",
    })
    assert resp.status_code in (400, 422)


def test_admin_endpoint_authorization_and_student_forbidden(test_client):
    from app.db import init_demo_users
    init_demo_users()
    unique_student = f"test.student.{uuid.uuid4().hex[:8]}@skillsetu.gov.in"
    reg_resp = test_client.post("/api/auth/register", json={
        "email": unique_student,
        "password": "Password@123",
        "full_name": "Test Student",
        "role": "STUDENT",
    })
    assert reg_resp.status_code == 201
    student_token = reg_resp.json()["access_token"]
    forbidden_resp = test_client.get("/api/admin/data-governance", headers={"Authorization": f"Bearer {student_token}"})
    assert forbidden_resp.status_code == 403

    admin_login = test_client.post("/api/auth/login", json={
        "email": "admin@skillsetu.gov.in",
        "password": "AdminPass@2026",
    })
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    allowed_resp = test_client.get("/api/admin/data-governance", headers={"Authorization": f"Bearer {admin_token}"})
    assert allowed_resp.status_code == 200


def test_existing_non_admin_account_never_overwritten_to_admin(test_client):
    from app.db import init_demo_users, get_user_by_email
    init_demo_users()
    student = get_user_by_email("student@skillsetu.gov.in")
    assert student is not None
    assert student.get("role") == "STUDENT"
    assert student.get("role") != "ADMIN"


def test_real_mode_does_not_silently_fallback_when_demo_auth_disabled(test_client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "demo_auth_enabled", False)
    monkeypatch.setattr(settings, "use_demo_data", False)
    resp = test_client.post("/api/auth/login", json={
        "email": "unprovisioned.user@skillsetu.gov.in",
        "password": "Password@123",
    })
    assert resp.status_code == 401


def test_all_standard_demo_logins_functional(test_client):
    from app.db import init_demo_users
    init_demo_users()
    accounts = [
        ("student@skillsetu.gov.in", "Password@123", "STUDENT"),
        ("employer@skillsetu.gov.in", "Password@123", "EMPLOYER"),
        ("institute@skillsetu.gov.in", "Password@123", "INSTITUTE"),
        ("government@skillsetu.gov.in", "Password@123", "GOVERNMENT"),
        ("admin@skillsetu.gov.in", "AdminPass@2026", "ADMIN"),
    ]
    for email, password, expected_role in accounts:
        resp = test_client.post("/api/auth/login", json={
            "email": email,
            "password": password,
        })
        assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
        data = resp.json()
        assert data["user"]["role"] == expected_role


def test_admin_provisioning_reuses_existing_auth_uuid_when_present(test_client, monkeypatch):
    import app.db as db_module

    updated_users = []
    upserted_rows = []

    class FakeAuthUser:
        id = "custom-auth-uuid-9999"
        email = "admin@skillsetu.gov.in"

    class FakeAdminAuth:
        def list_users(self):
            return [FakeAuthUser()]

        def update_user_by_id(self, uid, data):
            updated_users.append((uid, data))
            return {"id": uid}

        def create_user(self, data):
            raise AssertionError("create_user should not be called when user exists")

    class FakeAuth:
        admin = FakeAdminAuth()

    class FakeTable:
        def upsert(self, row, **kwargs):
            upserted_rows.append(row)
            return self

        def select(self, *args, **kwargs):
            return self

        def execute(self):
            return type("Resp", (), {"data": []})()

    class FakeClient:
        auth = FakeAuth()

        def table(self, name):
            return FakeTable()

    monkeypatch.setattr(db_module, "get_supabase_client", lambda: FakeClient())
    db_module.init_demo_users()

    assert len(updated_users) == 1
    assert updated_users[0][0] == "custom-auth-uuid-9999"
    assert len(upserted_rows) == 1
    assert upserted_rows[0]["id"] == "custom-auth-uuid-9999"


def test_admin_login_with_gotrue_success_and_public_users_reconciliation(test_client, monkeypatch):
    import app.routers.auth as auth_router
    import app.db as db_module

    upserted_records = []

    class FakeUserMetadata:
        full_name = "SkillSetu System Administrator"

    class FakeGoTrueUser:
        id = "73e35d08-a564-4cd2-b503-a641a8a0a5aa"
        email = "admin@skillsetu.gov.in"
        user_metadata = {"role": "ADMIN", "name": "SkillSetu System Administrator"}

    class FakeAuthResponse:
        user = FakeGoTrueUser()

    class FakeAuth:
        def sign_in_with_password(self, credentials):
            if credentials.get("email") == "admin@skillsetu.gov.in" and credentials.get("password") == "AdminPass@2026":
                return FakeAuthResponse()
            raise Exception("Invalid credentials")

    class FakeTable:
        def upsert(self, row, **kwargs):
            upserted_records.append(row)
            return self

        def select(self, *args, **kwargs):
            return self

        def eq(self, *args, **kwargs):
            return self

        def execute(self):
            return type("Resp", (), {"data": [{"id": "73e35d08-a564-4cd2-b503-a641a8a0a5aa", "role": "ADMIN"}]})()

    class FakeClient:
        auth = FakeAuth()

        def table(self, name):
            return FakeTable()

    fake_client_instance = FakeClient()
    monkeypatch.setattr(auth_router, "get_supabase_client", lambda: fake_client_instance)
    monkeypatch.setattr(db_module, "get_supabase_client", lambda: fake_client_instance)

    resp = test_client.post("/api/auth/login", json={
        "email": "admin@skillsetu.gov.in",
        "password": "AdminPass@2026",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "access_token" in data
    assert data["user"]["id"] == "73e35d08-a564-4cd2-b503-a641a8a0a5aa"
    assert data["user"]["role"] == "ADMIN"
    assert len(upserted_records) == 0


def test_admin_login_incorrect_password_returns_401(test_client, monkeypatch):
    import app.routers.auth as auth_router

    class FakeAuth:
        def sign_in_with_password(self, credentials):
            raise Exception("Invalid login credentials")

    class FakeClient:
        auth = FakeAuth()

        def table(self, name):
            raise AssertionError("table access should not occur on failed auth")

    monkeypatch.setattr(auth_router, "get_supabase_client", lambda: FakeClient())

    resp = test_client.post("/api/auth/login", json={
        "email": "admin@skillsetu.gov.in",
        "password": "WrongPassword@999",
    })
    assert resp.status_code == 401
    assert "access_token" not in resp.json()


def test_admin_login_fails_closed_when_reconciliation_fails(test_client, monkeypatch):
    import app.routers.auth as auth_router
    import app.db as db_module

    class FakeGoTrueUser:
        id = "73e35d08-a564-4cd2-b503-a641a8a0a5aa"
        email = "admin@skillsetu.gov.in"
        user_metadata = {"role": "ADMIN"}

    class FakeAuthResponse:
        user = FakeGoTrueUser()

    class FakeAuth:
        def sign_in_with_password(self, credentials):
            return FakeAuthResponse()

    class FakeClient:
        auth = FakeAuth()

        def table(self, name):
            raise RuntimeError("Database connection timeout during user upsert")

    fake_client_instance = FakeClient()
    monkeypatch.setattr(auth_router, "get_supabase_client", lambda: fake_client_instance)
    monkeypatch.setattr(db_module, "get_supabase_client", lambda: fake_client_instance)

    resp = test_client.post("/api/auth/login", json={
        "email": "admin@skillsetu.gov.in",
        "password": "AdminPass@2026",
    })
    assert resp.status_code == 500
    assert "access_token" not in resp.json()
    assert "reconciliation failed" in resp.json()["detail"].lower()


def test_user_cannot_obtain_admin_role_via_request_parameters(test_client):
    resp = test_client.post("/api/auth/login", json={
        "email": "student@skillsetu.gov.in",
        "password": "Password@123",
        "role": "ADMIN",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["role"] == "STUDENT"


def test_public_registration_cannot_specify_admin_role(test_client):
    resp = test_client.post("/api/auth/register", json={
        "email": "malicious@skillsetu.gov.in",
        "password": "Password@123",
        "full_name": "Malicious User",
        "role": "ADMIN",
    })
    assert resp.status_code == 422


def test_demo_auth_active_when_use_demo_data_is_false(test_client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "use_demo_data", False)
    monkeypatch.setattr(settings, "demo_auth_enabled", True)

    resp = test_client.post("/api/auth/login", json={
        "email": "student@skillsetu.gov.in",
        "password": "Password@123",
    })
    assert resp.status_code == 200
    assert resp.json()["user"]["role"] == "STUDENT"


def test_real_mode_does_not_silently_fallback_for_unregistered_user(test_client, monkeypatch):
    from app.config import settings
    import app.routers.auth as auth_router

    monkeypatch.setattr(settings, "use_demo_data", False)
    monkeypatch.setattr(settings, "demo_auth_enabled", False)
    monkeypatch.setattr(auth_router, "get_supabase_client", lambda: None)

    resp = test_client.post("/api/auth/login", json={
        "email": "nonexistent@skillsetu.gov.in",
        "password": "Password@123",
    })
    assert resp.status_code == 401


def test_admin_reconciliation_does_not_overwrite_unrelated_user(test_client, monkeypatch):
    import app.routers.auth as auth_router
    import app.db as db_module

    tables_state = {
        "users": [
            {
                "id": "73e35d08-a564-4cd2-b503-a641a8a0a5aa",
                "email": "admin@skillsetu.gov.in",
                "role": "ADMIN",
            },
            {
                "id": "usr-employee-9999",
                "email": "unrelated.employee@skillsetu.gov.in",
                "name": "Existing Unrelated Employee",
                "role": "EMPLOYEE",
            }
        ]
    }

    class FakeGoTrueUser:
        id = "73e35d08-a564-4cd2-b503-a641a8a0a5aa"
        email = "admin@skillsetu.gov.in"
        user_metadata = {"role": "ADMIN", "name": "SkillSetu System Administrator"}

    class FakeAuthResponse:
        user = FakeGoTrueUser()

    class FakeAuth:
        def sign_in_with_password(self, credentials):
            return FakeAuthResponse()

    class FakeTable:
        def upsert(self, row, **kwargs):
            existing_idx = next((i for i, r in enumerate(tables_state["users"]) if r.get("id") == row.get("id")), None)
            if existing_idx is not None:
                tables_state["users"][existing_idx] = row
            else:
                tables_state["users"].append(row)
            return self

        def select(self, *args, **kwargs):
            return self

        def eq(self, col, val):
            self._eq_filter = (col, val)
            return self

        def execute(self):
            filtered = tables_state["users"]
            if hasattr(self, "_eq_filter"):
                c, v = self._eq_filter
                filtered = [r for r in filtered if str(r.get(c)) == str(v)]
            return type("Resp", (), {"data": filtered})()

    class FakeClient:
        auth = FakeAuth()

        def table(self, name):
            return FakeTable()

    fake_client_instance = FakeClient()
    monkeypatch.setattr(auth_router, "get_supabase_client", lambda: fake_client_instance)
    monkeypatch.setattr(db_module, "get_supabase_client", lambda: fake_client_instance)

    resp = test_client.post("/api/auth/login", json={
        "email": "admin@skillsetu.gov.in",
        "password": "AdminPass@2026",
    })
    assert resp.status_code == 200

    unrelated_user = next((u for u in tables_state["users"] if u.get("id") == "usr-employee-9999"), None)
    assert unrelated_user is not None
    assert unrelated_user["email"] == "unrelated.employee@skillsetu.gov.in"
    assert unrelated_user["role"] == "EMPLOYEE"


def test_init_demo_users_detects_admin_on_later_page_and_does_not_call_create_user(monkeypatch):
    import app.db as db_module

    updated_ids = []
    create_called = []

    class FakeGoTrueUser:
        def __init__(self, uid, email):
            self.id = uid
            self.email = email

    class FakeAdminAPI:
        def list_users(self, page=1, per_page=100):
            if page == 1:
                return [FakeGoTrueUser(f"user-{i}", f"user{i}@example.com") for i in range(100)]
            elif page == 2:
                return [FakeGoTrueUser("gotrue-page-2-uuid", "admin@skillsetu.gov.in")]
            return []

        def update_user_by_id(self, uid, attributes):
            updated_ids.append((uid, attributes))
            return None

        def create_user(self, attributes):
            create_called.append(attributes)
            raise AssertionError("create_user should not be called when user exists on later page")

    class FakeAuth:
        admin = FakeAdminAPI()

    class FakeTable:
        def select(self, *args, **kwargs):
            return self

        def upsert(self, row, **kwargs):
            return self

        def execute(self):
            return type("Resp", (), {"data": []})()

    class FakeClient:
        auth = FakeAuth()

        def table(self, name):
            return FakeTable()

    fake_client_instance = FakeClient()
    monkeypatch.setattr(db_module, "get_supabase_client", lambda: fake_client_instance)

    db_module.init_demo_users()

    assert len(updated_ids) == 1
    assert updated_ids[0][0] == "gotrue-page-2-uuid"
    assert len(create_called) == 0

    admin_cached = [u for u in db_module._cache.get("users", []) if u.get("email") == "admin@skillsetu.gov.in"]
    assert len(admin_cached) >= 1
    assert all(u.get("id") == "gotrue-page-2-uuid" for u in admin_cached)


def test_init_demo_users_synchronizes_admin_uid_across_all_cached_records(monkeypatch):
    import app.db as db_module

    db_module._cache["users"] = [
        {
            "id": "usr-admin-001",
            "email": "admin@skillsetu.gov.in",
            "role": "ADMIN",
            "name": "Old Admin Name",
        }
    ]

    class FakeGoTrueUser:
        id = "73e35d08-a564-4cd2-b503-a641a8a0a5aa"
        email = "admin@skillsetu.gov.in"

    class FakeAdminAPI:
        def list_users(self, page=1, per_page=100):
            return [FakeGoTrueUser()]

        def update_user_by_id(self, uid, attributes):
            return None

    class FakeAuth:
        admin = FakeAdminAPI()

    class FakeTable:
        def select(self, *args, **kwargs):
            return self

        def upsert(self, row, **kwargs):
            return self

        def execute(self):
            return type("Resp", (), {"data": []})()

    class FakeClient:
        auth = FakeAuth()

        def table(self, name):
            return FakeTable()

    fake_client_instance = FakeClient()
    monkeypatch.setattr(db_module, "get_supabase_client", lambda: fake_client_instance)

    db_module.init_demo_users()

    admin_cached = [u for u in db_module._cache.get("users", []) if u.get("email") == "admin@skillsetu.gov.in"]
    assert len(admin_cached) >= 1
    assert all(u.get("id") == "73e35d08-a564-4cd2-b503-a641a8a0a5aa" for u in admin_cached)
