import pytest
from starlette.testclient import TestClient

from app.main import app
from app.core.security import create_access_token
from app.repositories import supabase_repository
from app.repositories.supabase_repository import (
    get_student_profile,
    upsert_student_profile,
    get_employee_profile,
    upsert_employee_profile,
    delete_student_profile,
    delete_employee_profile,
    SupabaseRepositoryError,
)

STUDENT_TOKEN = create_access_token({"sub": "usr-student-001", "email": "student@skillsetu.gov.in", "role": "STUDENT"})
STUDENT2_TOKEN = create_access_token({"sub": "usr-student-002", "email": "student2@skillsetu.gov.in", "role": "STUDENT"})
EMPLOYEE_TOKEN = create_access_token({"sub": "usr-employee-001", "email": "employee@skillsetu.gov.in", "role": "EMPLOYEE"})
EMPLOYER_TOKEN = create_access_token({"sub": "usr-employer-001", "email": "employer@skillsetu.gov.in", "role": "EMPLOYER"})
ADMIN_TOKEN = create_access_token({"sub": "usr-admin-001", "email": "admin@skillsetu.gov.in", "role": "ADMIN"})

STUDENT_HEADERS = {"Authorization": f"Bearer {STUDENT_TOKEN}"}
STUDENT2_HEADERS = {"Authorization": f"Bearer {STUDENT2_TOKEN}"}
EMPLOYEE_HEADERS = {"Authorization": f"Bearer {EMPLOYEE_TOKEN}"}
EMPLOYER_HEADERS = {"Authorization": f"Bearer {EMPLOYER_TOKEN}"}
ADMIN_HEADERS = {"Authorization": f"Bearer {ADMIN_TOKEN}"}


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_student_profile_lifecycle(client):
    delete_student_profile("usr-student-001")

    res_empty = client.get("/api/student/profile", headers=STUDENT_HEADERS)
    assert res_empty.status_code == 404

    create_payload = {
        "institution": "Government Polytechnic Pune",
        "degree": "Diploma in Computer Engineering",
        "education_level": "Diploma",
        "academic_year": "Final Year",
        "graduation_year": 2026,
        "desired_role": "AI Engineer",
        "preferred_location": "Pune",
        "career_interests": ["Artificial Intelligence", "Robotics"],
        "skills": [
            {"skill_name": "Python", "proficiency": "advanced"},
            {"skill_name": "python", "proficiency": "intermediate"},
            {"skill_name": "Machine Learning", "proficiency": "beginner"},
        ],
        "projects": [
            {
                "name": "Smart Irrigation IoT",
                "description": "Automated crop moisture system",
                "skills": ["Python", "IoT"],
                "url": "https://github.com/student/irrigation",
            }
        ],
        "certifications": [
            {
                "name": "TensorFlow Developer Certificate",
                "issuer": "Google Developers",
                "issue_date": "2025-06-15",
                "url": "https://certificate.google/tf-123",
            }
        ],
        "courses": [
            {
                "course_name": "Applied Machine Learning",
                "provider": "NPTEL",
                "status": "completed",
            }
        ],
    }

    res_create = client.post("/api/student/profile", json=create_payload, headers=STUDENT_HEADERS)
    assert res_create.status_code == 201
    created_data = res_create.json()["profile"]
    assert created_data["user_id"] == "usr-student-001"
    assert created_data["desired_role"] == "AI Engineer"
    assert created_data["target_role"] == "AI Engineer"
    assert created_data["institution"] == "Government Polytechnic Pune"
    assert len(created_data["skills"]) == 2
    assert len(created_data["projects"]) == 1
    assert len(created_data["certifications"]) == 1
    assert len(created_data["courses"]) == 1

    res_get = client.get("/api/student/profile", headers=STUDENT_HEADERS)
    assert res_get.status_code == 200
    retrieved = res_get.json()["profile"]
    assert retrieved["user_id"] == "usr-student-001"
    assert retrieved["preferred_location"] == "Pune"


def test_student_profile_partial_update(client):
    create_payload = {
        "institution": "Government Polytechnic Pune",
        "desired_role": "AI Engineer",
        "skills": [{"skill_name": "Python", "proficiency": "advanced"}],
    }
    client.post("/api/student/profile", json=create_payload, headers=STUDENT_HEADERS)

    patch_payload = {
        "desired_role": "Senior AI Systems Specialist",
        "preferred_location": "Mumbai",
    }
    res_patch = client.patch("/api/student/profile", json=patch_payload, headers=STUDENT_HEADERS)
    assert res_patch.status_code == 200
    patched = res_patch.json()["profile"]
    assert patched["desired_role"] == "Senior AI Systems Specialist"
    assert patched["preferred_location"] == "Mumbai"
    assert patched["institution"] == "Government Polytechnic Pune"


def test_student_skills_subresource_endpoints(client):
    create_payload = {
        "institution": "Government Polytechnic Pune",
        "desired_role": "AI Engineer",
        "skills": [{"skill_name": "Python", "proficiency": "advanced"}],
    }
    client.post("/api/student/profile", json=create_payload, headers=STUDENT_HEADERS)

    new_skills = {
        "skills": [
            {"skill_name": "FastAPI", "proficiency": "expert"},
            {"skill_name": "Docker", "proficiency": "intermediate"},
        ]
    }
    res_put = client.put("/api/student/profile/skills", json=new_skills, headers=STUDENT_HEADERS)
    assert res_put.status_code == 200
    assert len(res_put.json()["skills"]) == 2

    add_skill = {"skill_name": "Kubernetes", "proficiency": "beginner"}
    res_post = client.post("/api/student/profile/skills", json=add_skill, headers=STUDENT_HEADERS)
    assert res_post.status_code == 200
    assert any(s["skill_name"] == "Kubernetes" for s in res_post.json()["skills"])

    res_del = client.delete("/api/student/profile/skills/Docker", headers=STUDENT_HEADERS)
    assert res_del.status_code == 200
    assert all(s["skill_name"] != "Docker" for s in res_del.json()["skills"])


def test_employee_profile_lifecycle(client):
    delete_employee_profile("usr-employee-001")

    res_empty = client.get("/api/employee/profile", headers=EMPLOYEE_HEADERS)
    assert res_empty.status_code == 404

    create_payload = {
        "current_role": "Backend Engineer",
        "years_of_experience": 3.5,
        "industry": "IT/ITES",
        "education": "B.Tech Computer Science",
        "target_role": "Lead Architect",
        "preferred_location": "Pune",
        "skills": [
            {"skill_name": "Python", "proficiency": "advanced"},
            {"skill_name": "PostgreSQL", "proficiency": "intermediate"},
        ],
        "certifications": [
            {
                "name": "AWS Certified Solutions Architect",
                "issuer": "Amazon Web Services",
                "issue_date": "2024-11-10",
                "url": "https://aws.cert/123",
            }
        ],
    }

    res_create = client.post("/api/employee/profile", json=create_payload, headers=EMPLOYEE_HEADERS)
    assert res_create.status_code == 201
    emp_profile = res_create.json()["profile"]
    assert emp_profile["user_id"] == "usr-employee-001"
    assert emp_profile["current_role"] == "Backend Engineer"
    assert emp_profile["years_of_experience"] == 3.5
    assert len(emp_profile["skills"]) == 2

    res_get = client.get("/api/employee/profile", headers=EMPLOYEE_HEADERS)
    assert res_get.status_code == 200
    assert res_get.json()["profile"]["target_role"] == "Lead Architect"


def test_employee_profile_partial_update(client):
    create_payload = {
        "current_role": "Backend Engineer",
        "years_of_experience": 3.5,
    }
    client.post("/api/employee/profile", json=create_payload, headers=EMPLOYEE_HEADERS)

    patch_payload = {
        "years_of_experience": 4.0,
        "target_role": "Principal Systems Engineer",
    }
    res_patch = client.patch("/api/employee/profile", json=patch_payload, headers=EMPLOYEE_HEADERS)
    assert res_patch.status_code == 200
    patched = res_patch.json()["profile"]
    assert patched["years_of_experience"] == 4.0
    assert patched["target_role"] == "Principal Systems Engineer"
    assert patched["current_role"] == "Backend Engineer"


def test_proficiency_validation(client):
    invalid_skill = {
        "skills": [
            {"skill_name": "Python", "proficiency": "super_master"}
        ]
    }
    res = client.put("/api/student/profile/skills", json=invalid_skill, headers=STUDENT_HEADERS)
    assert res.status_code == 422


def test_unauthorized_access(client):
    res = client.get("/api/student/profile")
    assert res.status_code == 401

    res = client.get("/api/employee/profile")
    assert res.status_code == 401


def test_role_spoofing_prevention(client):
    res = client.get("/api/employee/profile", headers=STUDENT_HEADERS)
    assert res.status_code == 403

    res = client.get("/api/student/profile", headers=EMPLOYEE_HEADERS)
    assert res.status_code == 403


def test_cross_user_isolation(client):
    res = client.get("/api/student/profile", headers=STUDENT2_HEADERS)
    assert res.status_code == 404


def test_database_failure_handling(client, monkeypatch):
    def failing_get(user_id):
        raise SupabaseRepositoryError("Simulated database failure")

    monkeypatch.setattr(supabase_repository, "get_student_profile", failing_get)
    res = client.get("/api/student/profile", headers=STUDENT_HEADERS)
    assert res.status_code == 500
    assert "Database query failed" in res.json()["detail"]


def test_admin_access_allowed(client):
    res_student = client.get("/api/student/profile", headers=ADMIN_HEADERS)
    assert res_student.status_code in (200, 404)

    res_employee = client.get("/api/employee/profile", headers=ADMIN_HEADERS)
    assert res_employee.status_code in (200, 404)


def test_employee_registration_and_login(client):
    reg_payload = {
        "email": "fresh.employee@skillsetu.gov.in",
        "password": "Password@123",
        "full_name": "Fresh Employee Candidate",
        "role": "EMPLOYEE",
        "district": "Pune",
    }
    res_reg = client.post("/api/auth/register", json=reg_payload)
    assert res_reg.status_code == 201
    token = res_reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res_get = client.get("/api/employee/profile", headers=headers)
    assert res_get.status_code == 404


def test_subresource_update_404_when_no_profile(client, monkeypatch):
    monkeypatch.setattr(supabase_repository, "get_student_profile", lambda uid: None)
    res_skills = client.put(
        "/api/student/profile/skills",
        json={"skills": [{"skill_name": "Python", "proficiency": "expert"}]},
        headers=STUDENT_HEADERS,
    )
    assert res_skills.status_code == 404

    res_add_skill = client.post(
        "/api/student/profile/skills",
        json={"skill_name": "Python", "proficiency": "expert"},
        headers=STUDENT_HEADERS,
    )
    assert res_add_skill.status_code == 404

    res_proj = client.put(
        "/api/student/profile/projects",
        json={"projects": [{"name": "AI Drone"}]},
        headers=STUDENT_HEADERS,
    )
    assert res_proj.status_code == 404

    res_certs = client.put(
        "/api/student/profile/certifications",
        json={"certifications": [{"name": "Cloud Practitioner", "issuer": "AWS"}]},
        headers=STUDENT_HEADERS,
    )
    assert res_certs.status_code == 404

    res_courses = client.put(
        "/api/student/profile/courses",
        json={"courses": [{"course_name": "Deep Learning"}]},
        headers=STUDENT_HEADERS,
    )
    assert res_courses.status_code == 404


def test_taxonomy_resolution_failure_propagates_500(client, monkeypatch):
    def failing_list_skills(*args, **kwargs):
        raise SupabaseRepositoryError("Taxonomy unavailable")

    monkeypatch.setattr(supabase_repository, "list_skills", failing_list_skills)
    payload = {
        "target_role": "AI Engineer",
        "skills": [{"skill_name": "PyTorch", "proficiency": "expert"}],
    }
    res = client.post("/api/student/profile", json=payload, headers=STUDENT_HEADERS)
    assert res.status_code == 500
    assert "Database persistence failed" in res.json()["detail"]


def test_employee_experience_upper_bound_validation(client):
    payload = {
        "current_role": "Senior Engineer",
        "years_of_experience": 75.0,
    }
    res = client.post("/api/employee/profile", json=payload, headers=EMPLOYEE_HEADERS)
    assert res.status_code == 422

