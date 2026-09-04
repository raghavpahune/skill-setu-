from starlette.testclient import TestClient
from app.main import app
from app.core.security import create_access_token

client = TestClient(app)

def test_assessment_submission_and_me_resolution():
    token = create_access_token({
        "sub": "usr-student-001",
        "email": "student@skillsetu.gov.in",
        "role": "STUDENT",
        "full_name": "Aarav Patil",
    })
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Check schemes/recommended/me before assessment
    res_schemes_pre = client.get("/api/schemes/recommended/me", headers=headers)
    assert res_schemes_pre.status_code == 200
    assert "schemes" in res_schemes_pre.json()

    # 2. Check gov/opportunities/recommended/me before assessment
    res_opps_pre = client.get("/api/gov/opportunities/recommended/me", headers=headers)
    assert res_opps_pre.status_code == 200
    assert "opportunities" in res_opps_pre.json()

    # 3. Submit student diagnostic assessment
    payload = {
        "name": "Diagnostic Candidate",
        "education": "B.Tech Computer Science",
        "district": "Pune",
        "career_goal": "AI Engineer",
        "interests": ["AI / ML", "Data Science"],
        "current_skills": [
            {"skill_name": "Python", "proficiency": "intermediate"},
            {"skill_name": "SQL", "proficiency": "beginner"},
        ],
        "quiz_answers": {
            "q1": "b",
            "q2": "a",
            "q3": "c",
            "q4": "a",
            "q5": "b",
        },
    }

    submit_res = client.post("/api/student/assessment", json=payload, headers=headers)
    assert submit_res.status_code == 200, f"Submit failed: {submit_res.text}"
    ast = submit_res.json()["assessment"]
    assert ast["name"] == "Diagnostic Candidate"
    assert ast["career_goal"] == "AI Engineer"
    assert ast["user_id"] == "usr-student-001"
    assert "evaluation_summary" in ast
    assert ast["evaluation_summary"]["readiness_level"] in ("PRODUCTION_READY", "INTERMEDIATE_READY", "FOUNDATIONAL")

    # 4. Verify /student/me/passport now reflects the submitted assessment
    pass_res = client.get("/api/student/me/passport", headers=headers)
    assert pass_res.status_code == 200
    pass_data = pass_res.json()
    assert pass_data["target_role"] == "AI Engineer"
    assert pass_data["is_personalized"] is True
    assert pass_data["source"] == "USER_SUBMITTED"
    assert len(pass_data["current_skills"]) >= 2

    # 5. Verify /student/me/roadmap now reflects the submitted assessment
    road_res = client.get("/api/student/me/roadmap", headers=headers)
    assert road_res.status_code == 200
    road_data = road_res.json()
    assert road_data["target_role"] == "AI Engineer"
    assert "roadmap" in road_data

    # 6. Verify /student/recommendations/me now returns calculated recommendations
    rec_res = client.get("/api/student/recommendations/me", headers=headers)
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert "recommended_careers" in rec_data

    # 7. Verify schemes and gov opportunities recommendations now work for 'me'
    res_schemes_post = client.get("/api/schemes/recommended/me", headers=headers)
    assert res_schemes_post.status_code == 200

    res_opps_post = client.get("/api/gov/opportunities/recommended/me", headers=headers)
    assert res_opps_post.status_code == 200


def test_unassessed_student_schemes_and_opps():
    import uuid
    email = f"brand_new_student_{uuid.uuid4().hex[:8]}@skillsetu.gov.in"
    # Register a new student who has no assessment
    res = client.post("/api/auth/register", json={
        "email": email,
        "password": "Password@123",
        "full_name": "New Student",
        "role": "STUDENT",
    })
    assert res.status_code == 201
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify unassessed schemes returns 200 with status: unassessed
    res_schemes = client.get("/api/schemes/recommended/me", headers=headers)
    assert res_schemes.status_code == 200
    assert res_schemes.json().get("status") == "unassessed"

    # Verify unassessed opportunities returns 200 with status: unassessed
    res_opps = client.get("/api/gov/opportunities/recommended/me", headers=headers)
    assert res_opps.status_code == 200
    assert res_opps.json().get("status") == "unassessed"
