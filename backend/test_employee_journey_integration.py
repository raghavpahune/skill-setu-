import uuid
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.core.security import create_access_token
from app.db import save_user
from app.repositories.supabase_repository import delete_employee_profile


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_employee_profile_creation_and_passport_retrieval(client):
    user_id = f"usr-emp-pass-{uuid.uuid4().hex[:8]}"
    email = f"{user_id}@skillsetu.gov.in"
    save_user({
        "id": user_id,
        "email": email,
        "role": "EMPLOYEE",
        "full_name": "Rohan Deshmukh",
        "is_active": True,
    })
    token = create_access_token({"sub": user_id, "role": "EMPLOYEE", "email": email})
    headers = {"Authorization": f"Bearer {token}"}

    delete_employee_profile(user_id)

    profile_payload = {
        "current_role": "Software Developer",
        "years_of_experience": 3.0,
        "industry": "IT / Software Services",
        "education": "B.E Computer Engineering",
        "target_role": "AI Engineer",
        "preferred_location": "Pune",
        "skills": [
            {"skill_name": "Python", "proficiency": "advanced"},
            {"skill_name": "SQL", "proficiency": "intermediate"},
        ],
        "certifications": [
            {
                "name": "AWS Certified Developer",
                "issuer": "Amazon Web Services",
                "issue_date": "2025-02-15",
                "url": "https://aws.cert/dev-1",
            }
        ],
    }

    create_res = client.post("/api/employee/profile", json=profile_payload, headers=headers)
    assert create_res.status_code == 201
    assert create_res.json()["profile"]["target_role"] == "AI Engineer"

    pass_res = client.get("/api/student/me/passport", headers=headers)
    assert pass_res.status_code == 200
    pass_data = pass_res.json()
    assert pass_data["user_id"] == user_id
    assert pass_data["target_role"] == "AI Engineer"
    assert pass_data["is_personalized"] is True
    assert len(pass_data["current_skills"]) >= 2
    assert any("Python" in s["skill_name"] for s in pass_data["current_skills"])


def test_employee_career_recommendations(client):
    user_id = f"usr-emp-rec-{uuid.uuid4().hex[:8]}"
    email = f"{user_id}@skillsetu.gov.in"
    save_user({
        "id": user_id,
        "email": email,
        "role": "EMPLOYEE",
        "full_name": "Snehal Kulkarni",
        "is_active": True,
    })
    token = create_access_token({"sub": user_id, "role": "EMPLOYEE", "email": email})
    headers = {"Authorization": f"Bearer {token}"}

    delete_employee_profile(user_id)

    profile_payload = {
        "current_role": "Mechanical Engineer",
        "years_of_experience": 4.0,
        "industry": "Electric Vehicles & Automotive",
        "education": "B.Tech Mechanical",
        "target_role": "Smart Manufacturing Engineer",
        "preferred_location": "Pune",
        "skills": [
            {"skill_name": "AutoCAD", "proficiency": "advanced"},
            {"skill_name": "CNC Programming", "proficiency": "intermediate"},
        ],
        "certifications": [],
    }

    create_res = client.post("/api/employee/profile", json=profile_payload, headers=headers)
    assert create_res.status_code == 201

    rec_res = client.get("/api/student/recommendations/me", headers=headers)
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert rec_data["candidate_name"] == "Snehal Kulkarni"
    assert rec_data["target_career_goal"] == "Smart Manufacturing Engineer"
    assert "overall_readiness" in rec_data
    assert len(rec_data.get("recommended_careers", [])) >= 1


def test_employee_personalized_industry_alerts(client):
    user_id = f"usr-emp-alert-{uuid.uuid4().hex[:8]}"
    email = f"{user_id}@skillsetu.gov.in"
    save_user({
        "id": user_id,
        "email": email,
        "role": "EMPLOYEE",
        "full_name": "Amit Jadhav",
        "is_active": True,
    })
    token = create_access_token({"sub": user_id, "role": "EMPLOYEE", "email": email})
    headers = {"Authorization": f"Bearer {token}"}

    delete_employee_profile(user_id)

    profile_payload = {
        "current_role": "Data Analyst",
        "years_of_experience": 2.5,
        "industry": "IT / Software Services",
        "education": "B.Sc Statistics",
        "target_role": "AI Engineer",
        "preferred_location": "Mumbai",
        "skills": [
            {"skill_name": "Python", "proficiency": "advanced"},
            {"skill_name": "Machine Learning", "proficiency": "intermediate"},
        ],
        "certifications": [],
    }

    client.post("/api/employee/profile", json=profile_payload, headers=headers)

    alert_res = client.get(f"/api/student/industry-alerts?student_id={user_id}&domain=ai_ml", headers=headers)
    assert alert_res.status_code == 200
    alert_data = alert_res.json()
    assert "alerts" in alert_data
    assert len(alert_data["alerts"]) >= 1


def test_employee_copilot_transition_query(client):
    user_id = f"usr-emp-copilot-{uuid.uuid4().hex[:8]}"
    email = f"{user_id}@skillsetu.gov.in"
    save_user({
        "id": user_id,
        "email": email,
        "role": "EMPLOYEE",
        "full_name": "Pooja Gaikwad",
        "is_active": True,
    })
    token = create_access_token({"sub": user_id, "role": "EMPLOYEE", "email": email})
    headers = {"Authorization": f"Bearer {token}"}

    delete_employee_profile(user_id)

    profile_payload = {
        "current_role": "Electrical Maintenance Technician",
        "years_of_experience": 3.5,
        "industry": "Electric Vehicles & Automotive",
        "education": "Diploma Electrical",
        "target_role": "EV Powertrain Specialist",
        "preferred_location": "Pune",
        "skills": [
            {"skill_name": "Circuit Analysis", "proficiency": "expert"},
            {"skill_name": "EV Battery Technology", "proficiency": "intermediate"},
        ],
        "certifications": [],
    }

    client.post("/api/employee/profile", json=profile_payload, headers=headers)

    query_payload = {
        "question": "How can I transition from my current role to an advanced technology role in Maharashtra?",
        "role": "employee",
        "district": "Pune",
        "student_id": user_id,
        "is_demo": True,
    }

    copilot_res = client.post("/api/copilot/ask", json=query_payload, headers=headers)
    assert copilot_res.status_code == 200
    copilot_data = copilot_res.json()
    assert copilot_data["role"] == "employee"
    assert len(copilot_data.get("answer", "")) > 50


def test_employee_data_isolation_and_authorization(client):
    emp_id = f"usr-emp-iso-{uuid.uuid4().hex[:8]}"
    other_student_id = f"usr-std-iso-{uuid.uuid4().hex[:8]}"

    save_user({"id": emp_id, "email": f"{emp_id}@skillsetu.gov.in", "role": "EMPLOYEE", "full_name": "Target Employee", "is_active": True})
    save_user({"id": other_student_id, "email": f"{other_student_id}@skillsetu.gov.in", "role": "STUDENT", "full_name": "Other Student", "is_active": True})

    emp_token = create_access_token({"sub": emp_id, "role": "EMPLOYEE", "email": f"{emp_id}@skillsetu.gov.in"})
    student_token = create_access_token({"sub": other_student_id, "role": "STUDENT", "email": f"{other_student_id}@skillsetu.gov.in"})

    emp_headers = {"Authorization": f"Bearer {emp_token}"}
    student_headers = {"Authorization": f"Bearer {student_token}"}

    delete_employee_profile(emp_id)

    profile_payload = {
        "current_role": "Software Engineer",
        "years_of_experience": 2.0,
        "industry": "IT / Software Services",
        "education": "B.Tech IT",
        "target_role": "Cloud Architect",
        "preferred_location": "Pune",
        "skills": [{"skill_name": "Python", "proficiency": "advanced"}],
        "certifications": [],
    }

    client.post("/api/employee/profile", json=profile_payload, headers=emp_headers)

    cross_rec = client.get(f"/api/student/recommendations/{emp_id}", headers=student_headers)
    assert cross_rec.status_code == 403

    cross_pass = client.get(f"/api/student/{emp_id}/passport", headers=student_headers)
    assert cross_pass.status_code == 403
