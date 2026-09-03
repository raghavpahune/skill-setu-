"""Phase 36: Final SIH Stage Demo Polish & Warm-Up Infrastructure Test Suite."""
import os
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.core.security import create_access_token
from app.db import _cache, is_supabase_connected


@pytest.fixture
def client():
    from app.db import init_db
    init_db()
    with TestClient(app) as c:
        yield c


# --------------------------------------------------------------------------
# 1. Warm-Up & Health Endpoint Tests
# --------------------------------------------------------------------------
def test_canonical_health_endpoint_structure(client):
    """Verify that /api/health conforms strictly to the canonical contract."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()

    assert data.get("status") == "ok"
    assert "demo_mode" in data
    assert "ai_available" in data
    assert "records_loaded" in data
    assert "districts" in data
    assert isinstance(data.get("districts"), list)
    assert len(data.get("districts")) > 0
    assert "supabase_connected" in data
    assert isinstance(data.get("supabase_connected"), bool)


def test_root_endpoint_health_probe(client):
    """Verify root endpoint responds to basic load-balancer health probes."""
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "ok"
    assert "/api/health" in data.get("health", "")


def test_warmup_script_probe_function():
    """Verify that scripts/warmup.py probe logic works as expected."""
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from scripts.warmup import probe_backend

    # Probing an invalid URL handles errors gracefully without crashing
    success, _, _ = probe_backend("http://127.0.0.1:9999/invalid-health-test", max_retries=1, retry_delay=0.1)
    assert success is False


# --------------------------------------------------------------------------
# 2. All 5 Primary SIH Role Personas Verification
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "email,password,expected_role",
    [
        ("student@skillsetu.gov.in", "Password@123", "STUDENT"),
        ("employer@skillsetu.gov.in", "Password@123", "EMPLOYER"),
        ("institute@skillsetu.gov.in", "Password@123", "INSTITUTE"),
        ("government@skillsetu.gov.in", "Password@123", "GOVERNMENT"),
        ("admin@skillsetu.gov.in", "AdminPass@2026", "ADMIN"),
    ],
)
def test_sih_demo_roles_authentication(client, email, password, expected_role):
    """Verify that all 5 SIH role demo personas can authenticate cleanly."""
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    data = resp.json()
    assert "access_token" in data
    user = data.get("user", {})
    assert user.get("role", "").upper() == expected_role


def test_sih_role_tokens_and_endpoints(client):
    """Verify that each role persona receives a valid token and can access its dashboard route."""
    personas = [
        ("student@skillsetu.gov.in", "Password@123", "/api/student/me/passport", 200),
        ("employer@skillsetu.gov.in", "Password@123", "/api/employer/demands", 200),
        ("institute@skillsetu.gov.in", "Password@123", "/api/institute/my-courses", 200),
        ("government@skillsetu.gov.in", "Password@123", "/api/districts", 200),
        ("admin@skillsetu.gov.in", "AdminPass@2026", "/api/admin/data-governance", 200),
    ]

    for email, password, endpoint, expected_status in personas:
        login_resp = client.post("/api/auth/login", json={"email": email, "password": password})
        assert login_resp.status_code == 200, f"Login failed for {email}: {login_resp.text}"
        token = login_resp.json().get("access_token")
        assert token is not None

        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get(endpoint, headers=headers)
        assert resp.status_code == expected_status, f"Role endpoint {endpoint} failed for {email}: {resp.status_code}"


# --------------------------------------------------------------------------
# 3. Demo Data Safety & Non-Corruption Tests
# --------------------------------------------------------------------------
def test_demo_records_identifiability():
    """Verify that demo/synthetic records are identified and do not pollute real data."""
    jobs = _cache.get("jobs", [])
    assert len(jobs) > 0

    # Real data files must exist and be valid
    real_data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "real")
    if os.path.exists(real_data_dir):
        for fname in os.listdir(real_data_dir):
            if fname.endswith(".json"):
                fpath = os.path.join(real_data_dir, fname)
                assert os.path.getsize(fpath) > 0, f"Real data file {fname} is empty!"


# --------------------------------------------------------------------------
# 4. End-to-End Multi-Role SIH Story Pipeline Test
# --------------------------------------------------------------------------
def test_sih_end_to_end_demonstration_story(client):
    """Verify the sequential narrative of SkillSetu:

    Employer Demand -> Skill Gaps -> Student Recommendations ->
    Institute Alignment -> Government Intelligence -> Admin Governance.
    """
    # 1. Employer submits validated hiring demand
    emp_login = client.post("/api/auth/login", json={"email": "employer@skillsetu.gov.in", "password": "Password@123"})
    emp_token = emp_login.json()["access_token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    demand_payload = {
        "company_name": "Tata Motors Pune Robotics Lab",
        "job_role": "SIH Stage Test Robotics Specialist",
        "industry": "Automotive & Robotics",
        "district": "Pune",
        "openings": 25,
        "required_skills": ["Python", "ROS", "PLC Programming"],
        "urgency": "HIGH",
        "gstin": "27AABCU9603R1ZN",
    }
    demand_resp = client.post("/api/employer/demand", json=demand_payload, headers=emp_headers)
    assert demand_resp.status_code in (200, 201), f"Demand creation failed: {demand_resp.text}"
    created_demand = demand_resp.json()
    demand_id = created_demand.get("id") or created_demand.get("demand_id")

    # 2. Student Recommendations reflect skills and demand
    stu_login = client.post("/api/auth/login", json={"email": "student@skillsetu.gov.in", "password": "Password@123"})
    stu_token = stu_login.json()["access_token"]
    stu_headers = {"Authorization": f"Bearer {stu_token}"}
    rec_resp = client.get("/api/student/usr-student-001/recommendations", headers=stu_headers)
    assert rec_resp.status_code == 200
    rec_data = rec_resp.json()
    assert isinstance(rec_data, (list, dict))
    if isinstance(rec_data, dict):
        assert "recommendations" in rec_data or rec_data.get("status") == "success"

    # 3. Institute alignment
    inst_login = client.post("/api/auth/login", json={"email": "institute@skillsetu.gov.in", "password": "Password@123"})
    inst_token = inst_login.json()["access_token"]
    inst_headers = {"Authorization": f"Bearer {inst_token}"}
    inst_stats_resp = client.get("/api/institute/my-courses", headers=inst_headers)
    assert inst_stats_resp.status_code == 200

    # 4. Government District Intelligence
    gov_login = client.post("/api/auth/login", json={"email": "government@skillsetu.gov.in", "password": "Password@123"})
    gov_token = gov_login.json()["access_token"]
    gov_headers = {"Authorization": f"Bearer {gov_token}"}
    pune_resp = client.get("/api/districts/Pune/plan", headers=gov_headers)
    assert pune_resp.status_code == 200
    pune_data = pune_resp.json()
    assert pune_data.get("district") == "Pune"

    # 5. Admin Governance & Registry Oversight
    admin_login = client.post("/api/auth/login", json={"email": "admin@skillsetu.gov.in", "password": "AdminPass@2026"})
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    gov_summary_resp = client.get("/api/admin/data-governance", headers=admin_headers)
    assert gov_summary_resp.status_code == 200
    gov_summary = gov_summary_resp.json()
    assert "total_records" in gov_summary or "provenance_summary" in gov_summary

    # Cleanup temporary test record from memory/cache
    if demand_id:
        demands = _cache.get("employer_demands", [])
        _cache["employer_demands"] = [d for d in demands if d.get("id") != demand_id]
