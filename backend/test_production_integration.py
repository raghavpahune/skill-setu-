"""Automated Test Suite for Production Real-Data Integration, Scoping, and Deployment Topology.

Covers the 10 core production verification criteria:
1. Authenticated student -> personal passport
2. Student submits assessment -> submission persists
3. Student refresh -> same real assessment remains
4. Employer submits demand -> demand persists
5. Institute submits course -> course persists
6. Government publishes opportunity -> opportunity persists
7. Admin governance sees real vs demo provenance
8. Unauthorized user cannot access another user's personal data
9. API failure produces error/empty state, never a white screen
10. CORS/authentication behavior for production origins
"""
from datetime import datetime, timezone
import pytest
from starlette.testclient import TestClient
from app.main import app
import app.db as db

client = TestClient(app)

VERCEL_PROD_ORIGIN = "https://skill-setu-raghavpahune-8496.vercel.app"


def get_auth_token(email: str, password: str = "Password@123") -> str:
    """Helper to obtain JWT access token for a given user."""
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


def test_criterion_1_and_2_and_3_student_assessment_flow_and_refresh():
    """Criteria 1, 2, 3: Authenticated student submits assessment, persists, and survives refresh."""
    token = get_auth_token("student@skillsetu.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    unique_role = "Autonomous Vehicle Systems Engineer"
    payload = {
        "name": "Aarav Production Verification Candidate",
        "education": "B.Tech Mechatronics",
        "district": "Pune",
        "career_goal": unique_role,
        "interests": ["Robotics", "Autonomous Systems"],
        "current_skills": [
            {"skill_name": "PLC Programming", "proficiency": "advanced"},
            {"skill_name": "CAN Bus Diagnostics", "proficiency": "intermediate"},
        ],
        "quiz_answers": {"q1": "B", "q2": "A", "q3": "C", "q4": "A", "q5": "B"},
    }

    # 1. Post assessment (Criterion 2)
    post_res = client.post("/api/student/assessment", json=payload, headers=headers)
    assert post_res.status_code == 200
    saved = post_res.json().get("assessment", {})
    assert saved.get("source") == "USER_SUBMITTED"
    assert saved.get("is_demo") is False

    # 2. Get personal passport (Criterion 1)
    pass_res = client.get("/api/student/me/passport", headers=headers)
    assert pass_res.status_code == 200
    passport = pass_res.json()
    assert passport.get("is_personalized") is True
    assert passport.get("source") == "USER_SUBMITTED"
    assert passport.get("target_role") == unique_role

    # 3. Simulate browser refresh / subsequent GET (Criterion 3)
    refresh_res = client.get("/api/student/me/passport", headers=headers)
    assert refresh_res.status_code == 200
    refreshed_passport = refresh_res.json()
    assert refreshed_passport.get("target_role") == unique_role
    assert refreshed_passport.get("source") == "USER_SUBMITTED"


def test_criterion_4_employer_demand_persists():
    """Criterion 4: Employer submits demand, persists, and is returned via scoped me endpoint."""
    token = get_auth_token("employer@skillsetu.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    unique_title = "Lead Microgrid Engineer 2026"
    demand_payload = {
        "title": unique_title,
        "job_role": unique_title,
        "company": "Tata Power Renewable Energy",
        "industry": "Green Energy",
        "district": "Pune",
        "skills": ["Solar PV Systems", "Microgrid Architecture"],
        "required_skills": ["Solar PV Systems", "Microgrid Architecture"],
        "experience_level": "Mid-Senior Level (3-5 yrs)",
        "openings": 20,
        "openings_count": 20,
        "positions_count": 20,
        "urgency": "Immediate (within 30 days)",
        "hiring_timeline": "Immediate (within 30 days)",
        "preferred_proficiency": "advanced",
        "proficiency_required": "advanced",
        "nsqf_level": 6,
    }

    # 1. Post demand
    post_res = client.post("/api/employer/demands", json=demand_payload, headers=headers)
    assert post_res.status_code == 200
    saved = post_res.json().get("demand", {})
    demand_id = saved.get("id")
    assert demand_id is not None
    assert saved.get("source") in ("USER_SUBMITTED", "EMPLOYER_SUBMITTED")

    # 2. Retrieve via personal endpoint
    me_res = client.get("/api/employer/me/demands", headers=headers)
    assert me_res.status_code == 200
    my_demands = me_res.json().get("demands", [])
    assert any(d.get("id") == demand_id for d in my_demands)


def test_criterion_5_institute_course_persists():
    """Criterion 5: Institute submits course, persists, and is returned via scoped me endpoint."""
    token = get_auth_token("institute@skillsetu.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    unique_course = "Advanced Cyber-Physical Factory Systems"
    course_payload = {
        "name": unique_course,
        "institute_name": "Government Polytechnic Pune",
        "district": "Pune",
        "category": "Advanced Manufacturing",
        "description": "Comprehensive cyber-physical factory testbed curriculum.",
        "skills": ["PLC Programming", "SCADA", "Industrial IoT"],
        "nsqf_level": 6,
        "enrolment_capacity": 60,
        "placed_count": 48,
        "duration_weeks": 24,
        "certifications": "MSBTE Certified",
    }

    # 1. Post course
    post_res = client.post("/api/institute/courses", json=course_payload, headers=headers)
    assert post_res.status_code == 200
    saved = post_res.json().get("course", {})
    course_id = saved.get("id")
    assert course_id is not None
    assert saved.get("source") == "USER_SUBMITTED"

    # 2. Retrieve via personal endpoint
    me_res = client.get("/api/institute/me/courses", headers=headers)
    assert me_res.status_code == 200
    my_courses = me_res.json().get("courses", [])
    assert any(c.get("id") == course_id for c in my_courses)


def test_criterion_6_government_opportunity_persists():
    """Criterion 6: Government publishes opportunity, persists, and is searchable."""
    token = get_auth_token("government@skillsetu.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    unique_scheme = "Maharashtra Green Hydrogen Apprenticeship Scheme 2026"
    opp_payload = {
        "name": unique_scheme,
        "department": "Department of Skills & Renewable Energy",
        "description": "Comprehensive statewide training in green hydrogen safety.",
        "opportunity_type": "APPRENTICESHIP",
        "target_skills": ["Hydrogen Safety", "Cryogenic Piping"],
        "district_coverage": ["Pune", "Nashik", "Nagpur"],
        "application_url": "https://mssds.gov.in/hydrogen",
        "status": "active",
    }

    # 1. Publish opportunity
    post_res = client.post("/api/gov/opportunities", json=opp_payload, headers=headers)
    assert post_res.status_code == 201
    created = post_res.json().get("opportunity", {})
    opp_id = created.get("id")
    assert opp_id is not None
    assert created.get("source") == "USER_SUBMITTED"
    assert created.get("data_provenance") == "GOVERNMENT_OFFICIAL"

    # 2. Retrieve via query
    list_res = client.get(f"/api/gov/opportunities?q={unique_scheme}")
    assert list_res.status_code == 200
    found = [o for o in list_res.json() if o.get("id") == opp_id]
    assert len(found) == 1


def test_criterion_7_admin_governance_provenance():
    """Criterion 7: Admin governance dashboard segregates real user data from demo synthetic data."""
    token = get_auth_token("admin@skillsetu.gov.in", password="AdminPass@2026")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/admin/data-governance", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data.get("status") == "success"
    assert data.get("total_records") > 0
    assert data.get("total_real_user_submitted") > 0
    assert data.get("total_demo_synthetic") > 0
    assert "tables" in data


def test_criterion_8_unauthorized_user_cannot_access_private_data():
    """Criterion 8: Unauthorized users are blocked from accessing other users' personal records."""
    # 1. Unauthenticated request to /student/me/passport must return 401
    anon_res = client.get("/api/student/me/passport")
    assert anon_res.status_code == 401, "Unauthenticated request must be rejected with 401!"

    # 2. Register user A and create private assessment
    email_a = "candidate_a_privacy@skillsetu.gov.in"
    client.post("/api/auth/register", json={
        "email": email_a,
        "password": "Password@123",
        "full_name": "Candidate Alpha",
        "role": "STUDENT",
        "district": "Pune",
    })
    token_a = get_auth_token(email_a)
    headers_a = {"Authorization": f"Bearer {token_a}"}

    post_res = client.post("/api/student/assessment", json={
        "name": "Candidate Alpha",
        "education": "ITI Fitter",
        "district": "Pune",
        "career_goal": "CNC Specialist",
        "interests": ["Manufacturing"],
        "current_skills": [{"skill_name": "CAD/CAM", "proficiency": "beginner"}],
        "quiz_answers": {"q1": "A"},
    }, headers=headers_a)
    assert post_res.status_code == 200
    ast_id = post_res.json()["assessment"]["id"]

    # 3. Unauthenticated request to Candidate A's specific assessment ID must return 401
    anon_ast = client.get(f"/api/student/{ast_id}/passport")
    assert anon_ast.status_code == 401, "Anonymous requester cannot view private candidate assessment!"

    # 4. Candidate B trying to access Candidate A's assessment ID must return 403
    email_b = "candidate_b_privacy@skillsetu.gov.in"
    client.post("/api/auth/register", json={
        "email": email_b,
        "password": "Password@123",
        "full_name": "Candidate Beta",
        "role": "STUDENT",
        "district": "Mumbai",
    })
    token_b = get_auth_token(email_b)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    forbidden_ast = client.get(f"/api/student/{ast_id}/passport", headers=headers_b)
    assert forbidden_ast.status_code == 403, "Student B must NOT access Student A's personal assessment!"


def test_criterion_9_error_resilience_and_empty_states():
    """Criterion 9: API errors return clean JSON structure and health endpoint reports system status."""
    # 1. Non-existent resource returns structured 404 JSON, not unhandled 500
    res_404 = client.get("/api/institute/courses/cr-non-existent-999999")
    assert res_404.status_code == 404
    assert "detail" in res_404.json()

    # 2. Health check endpoint responds with 200 and operational details
    health_res = client.get("/api/health")
    assert health_res.status_code == 200
    health = health_res.json()
    assert health.get("status") in ("ok", "healthy")
    assert "tables_loaded" in health


def test_criterion_10_cors_headers_for_production_origin():
    """Criterion 10: Backend responds with proper CORS headers for the deployed Vercel domain."""
    headers = {
        "Origin": VERCEL_PROD_ORIGIN,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization,content-type",
    }

    # Preflight OPTIONS request
    opt_res = client.options("/api/health", headers=headers)
    assert opt_res.status_code == 200
    assert opt_res.headers.get("access-control-allow-origin") == VERCEL_PROD_ORIGIN
    assert opt_res.headers.get("access-control-allow-credentials") == "true"

    # Actual GET request with Origin
    get_res = client.get("/api/health", headers={"Origin": VERCEL_PROD_ORIGIN})
    assert get_res.status_code == 200
    assert get_res.headers.get("access-control-allow-origin") == VERCEL_PROD_ORIGIN
    assert get_res.headers.get("access-control-allow-credentials") == "true"
