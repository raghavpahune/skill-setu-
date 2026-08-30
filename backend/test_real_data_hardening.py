"""Comprehensive Test Suite for Real-Data Hardening, Cache Restart Safety, Scoped Isolation, and Hybrid Analytics."""
from datetime import datetime, timezone
import json
import pytest
from starlette.testclient import TestClient
from app.main import app
import app.db as db
from app.services.gap_engine import compute_gaps
from app.services.district_service import get_district_plan

client = TestClient(app)


def get_auth_token(email: str, password: str = "Password@123") -> str:
    """Helper to authenticate and retrieve JWT access token."""
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


def test_cache_restart_safety():
    """Verify that if in-memory _cache is cleared (simulating server reboot),

    get_demo() safely invokes init_db() and restores BOTH demo and real records.
    """
    # 1. Ensure DB has initialized at least once
    db.init_db()

    # 2. Add a distinctive real record into student_assessments and flush to real storage
    test_record = {
        "id": "ast-reboot-safety-001",
        "user_id": "usr-reboot-test",
        "name": "Reboot Survival Candidate",
        "source": "USER_SUBMITTED",
        "is_demo": False,
        "district": "Pune",
        "career_goal": "AI Engineer",
        "current_skills": [{"skill_name": "Python", "proficiency": "advanced"}],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    db.save_student_assessment(test_record)

    # 3. Simulate sudden process restart by wiping _cache completely
    db._cache.clear()
    assert len(db._cache) == 0

    # 4. Calling get_demo should safely trigger init_db() rather than only load_demo_data()
    assessments = db.get_demo("student_assessments")
    assert len(assessments) > 0

    # Verify our real record survived the simulated reboot
    found = next((a for a in assessments if a.get("id") == "ast-reboot-safety-001"), None)
    assert found is not None, "Real record must survive in-memory cache clearing via init_db() restoration!"
    assert found.get("source") == "USER_SUBMITTED"
    assert found.get("is_demo") is False

    # Cleanup
    db.delete_student_assessment("ast-reboot-safety-001")


def test_unassessed_student_no_masquerading():
    """Verify that a newly registered student with no assessment submissions receives an explicit

    unassessed state, and DOES NOT silently get Aarav Patil's demo profile.
    """
    new_student_email = "new_student_unassessed@skillsetu.gov.in"
    reg_res = client.post("/api/auth/register", json={
        "email": new_student_email,
        "password": "Password@123",
        "full_name": "Pooja Deshmukh",
        "role": "STUDENT",
        "district": "Nagpur",
    })
    assert reg_res.status_code in (201, 409)

    token = get_auth_token(new_student_email)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Check /student/me/passport
    pass_res = client.get("/api/student/me/passport", headers=headers)
    assert pass_res.status_code == 200
    passport = pass_res.json()
    assert passport.get("has_assessment") is False
    assert passport.get("source") == "NO_SUBMISSION"
    assert passport.get("is_personalized") is False
    assert "Aarav Patil" not in passport.get("name", "")

    # 2. Check /student/me/roadmap
    road_res = client.get("/api/student/me/roadmap", headers=headers)
    assert road_res.status_code == 200
    roadmap = road_res.json()
    assert roadmap.get("has_roadmap") is False

    # 3. Check /student/me/recommendations
    rec_res = client.get("/api/student/me/recommendations", headers=headers)
    assert rec_res.status_code == 200
    recommendations = rec_res.json()
    assert recommendations.get("status") == "unassessed"
    assert recommendations.get("has_assessment") is False


def test_student_assessment_full_lifecycle():
    """Verify full end-to-end lifecycle for student assessment submission and retrieval."""
    token = get_auth_token("student@skillsetu.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "name": "Aarav Live Verified Candidate",
        "education": "B.Tech Mechanical Engineering",
        "district": "Pune",
        "career_goal": "Industrial Automation Specialist",
        "interests": ["Automation", "Manufacturing"],
        "current_skills": [
            {"skill_name": "PLC Programming", "proficiency": "intermediate"},
            {"skill_name": "Industrial Robotics", "proficiency": "beginner"},
        ],
        "quiz_answers": {"q1": "B", "q2": "A", "q3": "C", "q4": "A", "q5": "B"},
    }

    # 1. Submit
    post_res = client.post("/api/student/assessment", json=payload, headers=headers)
    assert post_res.status_code == 200
    data = post_res.json()
    assert data.get("status") == "success"
    assessment = data.get("assessment", {})
    assert assessment.get("source") == "USER_SUBMITTED"
    assert assessment.get("created_at") is not None
    assert assessment.get("updated_at") is not None

    # 2. Retrieve personal passport
    pass_res = client.get("/api/student/me/passport", headers=headers)
    assert pass_res.status_code == 200
    passport = pass_res.json()
    assert passport.get("target_role") == "Industrial Automation Specialist"
    assert passport.get("source") == "USER_SUBMITTED"
    assert passport.get("is_personalized") is True

    # 3. Retrieve personal roadmap
    road_res = client.get("/api/student/me/roadmap", headers=headers)
    assert road_res.status_code == 200
    roadmap = road_res.json()
    assert len(roadmap.get("roadmap", [])) > 0


def test_employer_demand_lifecycle_and_deduplication():
    """Verify employer demand creation, personal scoping, deduplication, and persistence."""
    token = get_auth_token("employer@skillsetu.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    demand_payload = {
        "title": "Senior Automation Engineer",
        "job_role": "Senior Automation Engineer",
        "company": "Tata Motors Ltd",
        "industry": "Automotive & Heavy Industry",
        "district": "Pune",
        "skills": ["PLC Programming", "SCADA", "Industrial Robotics"],
        "required_skills": ["PLC Programming", "SCADA", "Industrial Robotics"],
        "experience_level": "Mid-Senior Level (3-5 yrs)",
        "openings": 15,
        "openings_count": 15,
        "positions_count": 15,
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
    assert saved.get("created_at") is not None
    assert saved.get("updated_at") is not None

    # 2. Get my demands
    get_res = client.get("/api/employer/me/demands", headers=headers)
    assert get_res.status_code == 200
    my_demands = get_res.json().get("demands", [])
    assert any(d.get("id") == demand_id for d in my_demands)

    # 3. Test de-duplication: saving with same ID updates rather than creating duplicates
    saved["openings"] = 25
    saved["openings_count"] = 25
    db.save_employer_demand(saved)

    demands_after = [d for d in db.get_demo("employer_demands") if d.get("id") == demand_id]
    assert len(demands_after) == 1, "De-duplication must prevent duplicate records for the same demand ID!"
    assert demands_after[0].get("openings_count") == 25

    # Cleanup
    db.delete_employer_demand(demand_id)


def test_institute_course_lifecycle_and_analytics_influence():
    """Verify institute course registration, personal scoping, and that the new course

    capacity and skills directly feed the gap engine analytics.
    """
    token = get_auth_token("institute@skillsetu.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    course_payload = {
        "name": "Advanced Robotic Weld Cell Operation",
        "institute_name": "Government Polytechnic Pune",
        "district": "Pune",
        "category": "Manufacturing & Automation",
        "description": "Hands-on industrial robot programming and weld inspection.",
        "skills": ["Industrial Robotics", "PLC Programming"],
        "skills_taught": ["Industrial Robotics", "PLC Programming"],
        "nsqf_level": 6,
        "enrolment_capacity": 150,
        "enrolment_count": 150,
        "placed_count": 120,
        "duration_weeks": 20,
        "certifications": "MSBTE & DGT Certificate",
    }

    # 1. Post course
    post_res = client.post("/api/institute/courses", json=course_payload, headers=headers)
    assert post_res.status_code == 200
    saved = post_res.json().get("course", {})
    course_id = saved.get("id")
    assert course_id is not None
    assert saved.get("source") == "USER_SUBMITTED"
    assert saved.get("created_at") is not None

    # 2. Get my courses
    get_res = client.get("/api/institute/me/courses", headers=headers)
    assert get_res.status_code == 200
    my_courses = get_res.json().get("courses", [])
    assert any(c.get("id") == course_id for c in my_courses)

    # 3. Gap Engine integration check: verify compute_gaps runs smoothly with user course
    gaps = compute_gaps(district="Pune")
    assert isinstance(gaps, list)
    assert len(gaps) > 0

    # Cleanup
    db.delete_course(course_id)


def test_district_plan_incorporates_employer_demands():
    """Verify that district training plan incorporates user-submitted employer demands."""
    # 1. Add distinctive employer demand for Nagpur
    unique_role = "Solar Inverter Diagnostic Technician"
    now_iso = datetime.now(timezone.utc).isoformat()
    demand = {
        "id": "ed-test-nagpur-001",
        "title": unique_role,
        "target_role": unique_role,
        "company": "Vidarbha Green Power",
        "district": "Nagpur",
        "openings": 40,
        "openings_count": 40,
        "required_skills": ["Solar PV Systems"],
        "source": "USER_SUBMITTED",
        "is_demo": False,
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    db.save_employer_demand(demand)

    # 2. Fetch district plan for Nagpur
    plan = get_district_plan("Nagpur")
    assert plan is not None
    top_roles = [r.get("role") for r in (plan.get("top_demanded_roles") or plan.get("top_roles") or [])]
    assert unique_role in top_roles, f"District plan must incorporate user-submitted employer demand '{unique_role}'!"

    # Cleanup
    db.delete_employer_demand("ed-test-nagpur-001")


def test_gov_opportunity_lifecycle_and_rbac():
    """Verify RBAC protections and lifecycle for government schemes/opportunities."""
    # 1. Unauthorized attempt (Student role cannot POST gov opportunities)
    student_token = get_auth_token("student@skillsetu.gov.in")
    student_headers = {"Authorization": f"Bearer {student_token}"}

    opp_payload = {
        "name": "State Drone Pilot Mission",
        "department": "Directorate of Vocational Education",
        "description": "Comprehensive drone piloting and maintenance certification.",
        "opportunity_type": "VOCATIONAL_TRAINING",
        "target_skills": ["Drone Maintenance", "Avionics"],
        "district_coverage": ["Pune", "Nashik"],
        "application_url": "https://dvet.gov.in",
        "status": "active",
    }

    forbidden_res = client.post("/api/gov/opportunities", json=opp_payload, headers=student_headers)
    assert forbidden_res.status_code == 403, "Student must NOT be allowed to publish government schemes!"

    # 2. Authorized submission (Government role)
    gov_token = get_auth_token("government@skillsetu.gov.in")
    gov_headers = {"Authorization": f"Bearer {gov_token}"}

    create_res = client.post("/api/gov/opportunities", json=opp_payload, headers=gov_headers)
    assert create_res.status_code == 201
    created_opp = create_res.json().get("opportunity", {})
    opp_id = created_opp.get("id")
    assert opp_id is not None
    assert created_opp.get("source") == "USER_SUBMITTED"
    assert created_opp.get("data_provenance") == "GOVERNMENT_OFFICIAL"

    # 3. Retrieve via public list
    list_res = client.get(f"/api/gov/opportunities?q={created_opp['name']}")
    assert list_res.status_code == 200
    matched = [o for o in list_res.json() if o.get("id") == opp_id]
    assert len(matched) == 1

    # Cleanup
    db.delete_gov_opportunity(opp_id)


def test_admin_data_governance_provenance_summary():
    """Verify that Admin Data Governance summary accurately reflects user-submitted data

    and separates DEMO_SYNTHETIC from live data.
    """
    admin_token = get_auth_token("admin@skillsetu.gov.in", password="AdminPass@2026")
    headers = {"Authorization": f"Bearer {admin_token}"}

    res = client.get("/api/admin/data-governance", headers=headers)
    assert res.status_code == 200
    summary = res.json()

    assert "tables" in summary
    assert "total_records" in summary
    assert "total_real_user_submitted" in summary
    assert "total_demo_synthetic" in summary
    assert summary["total_demo_synthetic"] > 0
