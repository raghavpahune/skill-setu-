"""Comprehensive Test Suite for Real Data + Demo Data Hybrid Architecture."""
import os
import json
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.db import (
    init_db,
    get_demo,
    get_data_governance_summary,
    _find_real_data_dir,
)

client = TestClient(app)


def get_auth_token(email: str, password: str = "Password@123") -> str:
    """Helper to authenticate and retrieve JWT access token."""
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


def test_baseline_demo_synthetic_intact():
    """Verify demo baseline is loaded and marked DEMO_SYNTHETIC when no real data exists."""
    jobs = get_demo("jobs")
    skills = get_demo("skills")
    courses = get_demo("courses")
    
    assert len(jobs) >= 500
    assert len(skills) >= 50
    assert len(courses) >= 20
    
    # Check provenance
    demo_sample = [j for j in jobs if j.get("is_demo") is True or j.get("source") == "DEMO_SYNTHETIC"]
    assert len(demo_sample) > 0


def test_real_student_assessment_persistence_and_scoping():
    """Verify student submission persists to local disk, updates me/passport, and isolates identity."""
    token = get_auth_token("student@skillsetu.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Submit a real assessment
    payload = {
        "name": "Aarav Live Candidate",
        "education": "B.Tech Computer Science (COEP)",
        "district": "Pune",
        "career_goal": "AI Engineer",
        "interests": ["AI / ML", "Data Science"],
        "current_skills": [
            {"skill_name": "Python", "proficiency": "advanced"},
            {"skill_name": "Generative AI", "proficiency": "intermediate"},
            {"skill_name": "Vector Databases", "proficiency": "beginner"},
        ],
        "quiz_answers": {"q1": "A", "q2": "B", "q3": "A", "q4": "C", "q5": "B"},
    }

    res_post = client.post("/api/student/assessment", json=payload, headers=headers)
    assert res_post.status_code == 200
    post_data = res_post.json()
    assert post_data["status"] == "success"
    assessment_id = post_data["assessment"]["id"]
    assert post_data["assessment"]["source"] == "USER_SUBMITTED"
    assert post_data["assessment"]["is_demo"] is False

    # 2. Verify disk persistence in data/real/student_assessments.json
    real_dir = _find_real_data_dir()
    real_file = real_dir / "student_assessments.json"
    assert real_file.exists()
    file_records = json.loads(real_file.read_text(encoding="utf-8"))
    assert any(r["id"] == assessment_id for r in file_records)

    # 3. Verify GET /student/me/passport returns this real assessment data
    res_passport = client.get("/api/student/me/passport", headers=headers)
    assert res_passport.status_code == 200
    pass_data = res_passport.json()
    assert pass_data["source"] == "USER_SUBMITTED"
    assert pass_data["is_personalized"] is True
    assert pass_data["target_role"] == "AI Engineer"
    assert any(s["skill_name"] == "Generative AI" for s in pass_data["current_skills"])

    # 4. Verify GET /student/me/roadmap computes from real assessment
    res_roadmap = client.get("/api/student/me/roadmap", headers=headers)
    assert res_roadmap.status_code == 200
    roadmap_data = res_roadmap.json()
    assert "roadmap" in roadmap_data
    assert len(roadmap_data["roadmap"]) > 0


def test_reboot_simulation_restores_real_data_from_disk():
    """Verify that simulating a backend server restart (calling init_db()) reloads disk-persisted real submissions."""
    # Re-initialize DB from scratch
    init_db()

    token = get_auth_token("student@skillsetu.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    # Verify that the student's personal passport is still loaded from data/real
    res = client.get("/api/student/me/passport", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["source"] == "USER_SUBMITTED"
    assert data["is_personalized"] is True


def test_real_employer_demand_submission_and_scoping():
    """Verify employer demand is assigned USER_SUBMITTED, persisted to disk, and returned in me/demands."""
    token = get_auth_token("employer@skillsetu.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "company_name": "Tata Motors EV Tech",
        "employer_name": "Tata Motors EV Tech",
        "industry": "Automotive & Clean Energy",
        "district": "Pune",
        "job_role": "High-Voltage Battery Diagnostic Specialist",
        "role_title": "High-Voltage Battery Diagnostic Specialist",
        "required_skills": ["EV Battery Technology", "Battery Management (BMS)", "CAN Bus Diagnostics"],
        "skills": ["EV Battery Technology", "Battery Management (BMS)", "CAN Bus Diagnostics"],
        "preferred_proficiency": "advanced",
        "proficiency_required": "advanced",
        "nsqf_level": 6,
        "hiring_timeline": "Immediate (0-30 days)",
        "openings_count": 25,
        "positions_count": 25,
        "experience_level": "Mid Level (1-3 yrs)",
    }

    res_post = client.post("/api/employer/demands", json=payload, headers=headers)
    assert res_post.status_code == 200
    post_data = res_post.json()
    demand_id = post_data["demand"]["id"]
    assert post_data["demand"]["source"] == "EMPLOYER_SUBMITTED"
    assert post_data["demand"]["is_demo"] is False


    # Check disk persistence
    real_dir = _find_real_data_dir()
    real_file = real_dir / "employer_demands.json"
    assert real_file.exists()
    demands_on_disk = json.loads(real_file.read_text(encoding="utf-8"))
    assert any(d["id"] == demand_id for d in demands_on_disk)

    # Scoped GET /employer/me/demands
    res_mine = client.get("/api/employer/me/demands", headers=headers)
    assert res_mine.status_code == 200
    mine_data = res_mine.json()
    assert any(d["id"] == demand_id for d in mine_data["demands"])


def test_real_institute_course_submission_and_filtering():
    """Verify institute course submission is persisted, scoped, and queryable with provenance filter."""
    token = get_auth_token("institute@skillsetu.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "name": "Advanced EV Powertrain & BMS Diagnostics",
        "institute_name": "Government Polytechnic Pune",
        "district": "Pune",
        "category": "Automotive & Clean Energy",
        "description": "Hands-on vocational certification in EV high-voltage battery assembly and motor calibration.",
        "skills": ["EV Battery Technology", "Battery Management (BMS)", "Motor Control"],
        "nsqf_level": 6,
        "enrolment_capacity": 80,
        "placed_count": 68,
        "duration_weeks": 24,
        "certifications": "MSBTE Advanced Certificate in EV Systems",
        "status": "active",
    }

    res_post = client.post("/api/institute/courses", json=payload, headers=headers)
    assert res_post.status_code == 200
    post_data = res_post.json()
    course_id = post_data["course"]["id"]
    assert post_data["course"]["source"] == "USER_SUBMITTED"
    assert post_data["course"]["is_demo"] is False

    # Check disk persistence
    real_dir = _find_real_data_dir()
    real_file = real_dir / "courses.json"
    assert real_file.exists()
    courses_on_disk = json.loads(real_file.read_text(encoding="utf-8"))
    assert any(c["id"] == course_id for c in courses_on_disk)

    # Scoped GET /institute/me/courses
    res_mine = client.get("/api/institute/me/courses", headers=headers)
    assert res_mine.status_code == 200
    mine_data = res_mine.json()
    assert any(c["id"] == course_id for c in mine_data["courses"])

    # Query with provenance filter
    res_user_sub = client.get("/api/institute/courses?source=USER_SUBMITTED")
    assert res_post.status_code == 200
    assert any(c["id"] == course_id for c in res_user_sub.json())


def test_admin_data_governance_breakdown():
    """Verify admin data governance API reports live vs demo counts accurately."""
    token = get_auth_token("admin@skillsetu.gov.in", "AdminPass@2026")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/admin/data-governance", headers=headers)
    assert res.status_code == 200
    gov = res.json()
    assert gov["status"] == "success"
    assert gov["total_real_user_submitted"] > 0
    assert gov["total_demo_synthetic"] > 0
    assert gov["live_data_active"] is True
    assert "student_assessments" in gov["tables"]
    assert "employer_demands" in gov["tables"]
    assert "courses" in gov["tables"]


def test_unauthorized_personal_endpoints_rejected():
    """Verify unauthenticated requests cannot access scoped endpoints."""
    res = client.get("/api/student/me/passport")
    assert res.status_code in (401, 403)

    res_emp = client.get("/api/employer/me/demands")
    assert res_emp.status_code in (401, 403)

    res_inst = client.get("/api/institute/me/courses")
    assert res_inst.status_code in (401, 403)
