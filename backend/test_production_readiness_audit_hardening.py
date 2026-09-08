import os
import uuid
from typing import Any
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.core.security import create_access_token
from app.db import save_user
from app.repositories import supabase_repository
from app.services.roadmap_service import compute_adaptive_roadmap


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers_student():
    student_id = f"usr-std-{uuid.uuid4().hex[:8]}"
    email = f"{student_id}@test.gov.in"
    save_user({"id": student_id, "email": email, "role": "STUDENT", "full_name": "Pooja Deshmukh", "is_active": True})
    token = create_access_token({"sub": student_id, "role": "STUDENT", "email": email})
    return student_id, {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_other_student():
    other_id = f"usr-std-{uuid.uuid4().hex[:8]}"
    email = f"{other_id}@test.gov.in"
    save_user({"id": other_id, "email": email, "role": "STUDENT", "full_name": "Candidate B", "is_active": True})
    token = create_access_token({"sub": other_id, "role": "STUDENT", "email": email})
    return other_id, {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_gov():
    gov_id = f"usr-gov-{uuid.uuid4().hex[:8]}"
    email = f"{gov_id}@maharashtra.gov.in"
    save_user({"id": gov_id, "email": email, "role": "GOVERNMENT", "full_name": "Director of Industry", "is_active": True})
    token = create_access_token({"sub": gov_id, "role": "GOVERNMENT", "email": email})
    return gov_id, {"Authorization": f"Bearer {token}"}


def test_student_profile_full_field_persistence(client, auth_headers_student):
    student_id, headers = auth_headers_student

    payload = {
        "full_name": "Pooja Deshmukh",
        "institution": "COEP Technological University",
        "degree": "B.Tech Computer Engineering",
        "education_level": "Undergraduate (B.Tech / B.E / B.Sc)",
        "academic_year": "Final Year",
        "graduation_year": 2026,
        "desired_role": "AI Engineer",
        "target_role": "AI Engineer",
        "preferred_location": "Pune",
        "career_interests": ["Machine Learning", "Autonomous Systems"],
        "skills": [
            {"skill_name": "Python", "proficiency": "expert"},
            {"skill_name": "PyTorch", "proficiency": "intermediate"},
        ],
        "projects": [
            {
                "name": "Edge RAG Copilot",
                "description": "On-device retrieval augmented generation system.",
                "skills": ["Python", "PyTorch"],
                "url": "https://github.com/pooja/edge-rag",
            }
        ],
        "certifications": [
            {
                "name": "NPTEL Deep Learning",
                "issuer": "IIT Madras",
                "issue_date": "2025-11-15",
                "url": "https://nptel.ac.in/cert/12345",
            }
        ],
        "courses": [
            {
                "course_name": "Advanced Neural Networks",
                "provider": "Coursera",
                "status": "completed",
            }
        ],
        "experience": [
            {
                "company": "Tata Elxsi",
                "role": "AI Research Intern",
                "duration": "Jun 2025 - Aug 2025",
                "description": "Developed computer vision models for driver assistance systems.",
            }
        ],
    }

    create_res = client.post("/api/student/profile", json=payload, headers=headers)
    assert create_res.status_code == 201
    created_profile = create_res.json()["profile"]

    assert created_profile["user_id"] == student_id
    assert created_profile["full_name"] == "Pooja Deshmukh"
    assert created_profile["institution"] == "COEP Technological University"
    assert len(created_profile["skills"]) == 2
    assert len(created_profile["projects"]) == 1
    assert len(created_profile["certifications"]) == 1
    assert len(created_profile["courses"]) == 1
    assert len(created_profile["experience"]) == 1
    assert created_profile["experience"][0]["company"] == "Tata Elxsi"

    get_res = client.get("/api/student/profile", headers=headers)
    assert get_res.status_code == 200
    fetched_profile = get_res.json()["profile"]
    assert fetched_profile["user_id"] == student_id
    assert fetched_profile["full_name"] == "Pooja Deshmukh"
    assert fetched_profile["institution"] == "COEP Technological University"
    assert fetched_profile["experience"][0]["role"] == "AI Research Intern"

    patch_payload = {
        "preferred_location": "Mumbai",
        "experience": [
            {
                "company": "Tata Elxsi",
                "role": "Lead AI Intern",
                "duration": "Jun 2025 - Nov 2025",
                "description": "Led team of 4 interns on vision models.",
            }
        ],
    }
    patch_res = client.patch("/api/student/profile", json=patch_payload, headers=headers)
    assert patch_res.status_code == 200
    patched_profile = patch_res.json()["profile"]
    assert patched_profile["preferred_location"] == "Mumbai"
    assert patched_profile["institution"] == "COEP Technological University"
    assert patched_profile["experience"][0]["role"] == "Lead AI Intern"


def test_student_profile_idor_protection(client, auth_headers_student, auth_headers_other_student):
    student_a, headers_a = auth_headers_student
    student_b, headers_b = auth_headers_other_student

    payload_a = {
        "full_name": "Candidate A",
        "institution": "Institute A",
        "degree": "Degree A",
        "skills": [{"skill_name": "Java", "proficiency": "intermediate"}],
    }
    create_res = client.post("/api/student/profile", json=payload_a, headers=headers_a)
    assert create_res.status_code == 201

    passport_res_b = client.get(f"/api/student/{student_a}/passport", headers=headers_b)
    assert passport_res_b.status_code == 403


def test_cross_feature_roadmap_adaptation_on_skill_change(client, auth_headers_student):
    student_id, headers = auth_headers_student

    beginner_payload = {
        "full_name": "Rahul Patil",
        "institution": "VJTI Mumbai",
        "degree": "B.Tech Computer Science",
        "desired_role": "AI Engineer",
        "target_role": "AI Engineer",
        "skills": [
            {"skill_name": "Python", "proficiency": "beginner"},
        ],
    }
    create_res = client.post("/api/student/profile", json=beginner_payload, headers=headers)
    assert create_res.status_code == 201

    roadmap_initial = compute_adaptive_roadmap(student_id=student_id, target_role="AI Engineer", is_demo=False, persist=False)
    assert roadmap_initial["has_roadmap"] is True
    python_step_initial = next((s for s in roadmap_initial["roadmap"] if "python" in s["skill_name"].lower()), None)
    assert python_step_initial is not None
    assert python_step_initial["status"] == "REVIEW"

    expert_payload = {
        "skills": [
            {"skill_name": "Python", "proficiency": "expert"},
        ],
    }
    put_skills_res = client.put("/api/student/profile/skills", json=expert_payload, headers=headers)
    assert put_skills_res.status_code == 200

    roadmap_adapted = compute_adaptive_roadmap(student_id=student_id, target_role="AI Engineer", is_demo=False, persist=False)
    python_step_adapted = next((s for s in roadmap_adapted["roadmap"] if "python" in s["skill_name"].lower()), None)
    assert python_step_adapted is not None
    assert python_step_adapted["status"] == "SKIP"


def test_gov_opportunity_publishing_and_persistence(client, auth_headers_gov, auth_headers_student):
    gov_id, gov_headers = auth_headers_gov
    student_id, student_headers = auth_headers_student

    opp_payload = {
        "name": "Maharashtra Green Hydrogen Apprenticeship Scheme 2026",
        "department": "Department of Energy, Govt of Maharashtra",
        "description": "Comprehensive one-year subsidized apprenticeship training for solar and green hydrogen production facilities in Chandrapur and Nagpur.",
        "eligibility_criteria": "Diploma or Degree in Chemical, Mechanical, or Electrical Engineering.",
        "target_skills": ["Green Hydrogen", "Solar PV Systems", "Industrial Safety"],
        "district_coverage": ["Nagpur", "Chandrapur"],
        "opportunity_type": "APPRENTICESHIP",
        "application_url": "https://mahaswayam.gov.in/green-hydrogen-2026",
        "deadline": "2026-12-31",
        "status": "active",
    }

    student_res = client.post("/api/gov/opportunities", json=opp_payload, headers=student_headers)
    assert student_res.status_code == 403

    gov_res = client.post("/api/gov/opportunities", json=opp_payload, headers=gov_headers)
    assert gov_res.status_code == 201
    created_opp = gov_res.json()["opportunity"]
    assert created_opp["name"] == opp_payload["name"]
    assert created_opp["source"] == "USER_SUBMITTED"
    assert created_opp["is_demo"] is False
    assert created_opp["user_id"] == gov_id

    list_res = client.get("/api/gov/opportunities?q=Green+Hydrogen")
    assert list_res.status_code == 200
    opps_list = list_res.json() if isinstance(list_res.json(), list) else list_res.json().get("opportunities", [])
    matched = next((o for o in opps_list if o["id"] == created_opp["id"]), None)
    assert matched is not None
    assert matched["department"] == opp_payload["department"]


def test_skill_passport_resolves_all_fields_for_profile_without_assessment(client, auth_headers_student):
    student_id, headers = auth_headers_student

    profile_payload = {
        "full_name": "Siddharth Shinde",
        "institution": "Government College of Engineering Karad",
        "degree": "B.Tech IT",
        "desired_role": "Cloud Architect",
        "target_role": "Cloud Architect",
        "skills": [
            {"skill_name": "Docker", "proficiency": "advanced"},
            {"skill_name": "Kubernetes", "proficiency": "intermediate"},
        ],
    }
    create_res = client.post("/api/student/profile", json=profile_payload, headers=headers)
    assert create_res.status_code == 201

    passport_res = client.get("/api/student/me/passport", headers=headers)
    assert passport_res.status_code == 200
    passport = passport_res.json()
    assert passport["name"] == "Siddharth Shinde"
    assert passport["target_role"] == "Cloud Architect"
    assert passport["is_personalized"] is True
    assert len(passport["current_skills"]) == 2
    assert all(cs["skill_name"] != "" for cs in passport["current_skills"])
    assert len(passport["required_skills"]) > 0
    assert all(rs["skill_name"] != "" for rs in passport["required_skills"])
