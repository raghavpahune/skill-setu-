import pytest
from app.services.student_service import (
    get_personalized_diagnostic_questions,
    evaluate_student_assessment,
    ALL_DIAGNOSTIC_QUESTIONS_MAP,
)
from app.repositories import supabase_repository


def test_incomplete_profile_returns_incomplete_status(monkeypatch):
    monkeypatch.setattr(supabase_repository, "get_student_profile", lambda student_id: None)
    result = get_personalized_diagnostic_questions("user-no-profile")
    assert result["status"] == "profile_incomplete"
    assert len(result["questions"]) == 0

    monkeypatch.setattr(supabase_repository, "get_student_profile", lambda student_id: {"user_id": student_id, "skills": []})
    result2 = get_personalized_diagnostic_questions("user-empty-profile")
    assert result2["status"] == "profile_incomplete"
    assert len(result2["questions"]) == 0


def test_software_student_personalization(monkeypatch):
    mock_profile = {
        "user_id": "user-sw-1",
        "target_role": "Full Stack Developer",
        "degree": "B.Tech Computer Science",
        "education_level": "Undergraduate",
        "skills": [{"skill_name": "Python", "proficiency": "intermediate"}, {"skill_name": "Git", "proficiency": "advanced"}],
        "career_interests": ["software", "web_dev"],
    }
    monkeypatch.setattr(supabase_repository, "get_student_profile", lambda student_id: mock_profile)
    result = get_personalized_diagnostic_questions("user-sw-1")
    assert result["status"] == "success"
    assert result["domain"] == "software"
    assert len(result["questions"]) == 5
    q_ids = [q["id"] for q in result["questions"]]
    assert any(q_id.startswith("q_sw_") for q_id in q_ids)


def test_ai_ml_student_personalization(monkeypatch):
    mock_profile = {
        "user_id": "user-ai-1",
        "target_role": "AI Engineer",
        "degree": "B.Tech Data Science",
        "education_level": "Undergraduate",
        "skills": [{"skill_name": "Machine Learning", "proficiency": "advanced"}, {"skill_name": "PyTorch", "proficiency": "intermediate"}],
        "career_interests": ["ai_ml", "data_science"],
    }
    monkeypatch.setattr(supabase_repository, "get_student_profile", lambda student_id: mock_profile)
    result = get_personalized_diagnostic_questions("user-ai-1")
    assert result["status"] == "success"
    assert result["domain"] == "ai_ml"
    assert len(result["questions"]) == 5
    q_ids = [q["id"] for q in result["questions"]]
    assert any(q_id.startswith("q_ai_") or q_id.startswith("q_ds_") for q_id in q_ids)


def test_mechanical_student_personalization(monkeypatch):
    mock_profile = {
        "user_id": "user-mech-1",
        "target_role": "Smart Manufacturing Engineer",
        "degree": "Diploma Mechanical Engineering",
        "education_level": "Diploma",
        "skills": [{"skill_name": "AutoCAD", "proficiency": "intermediate"}, {"skill_name": "CNC Programming", "proficiency": "intermediate"}],
        "career_interests": ["manufacturing", "robotics"],
    }
    monkeypatch.setattr(supabase_repository, "get_student_profile", lambda student_id: mock_profile)
    result = get_personalized_diagnostic_questions("user-mech-1")
    assert result["status"] == "success"
    assert result["domain"] == "mechanical"
    assert len(result["questions"]) == 5
    q_ids = [q["id"] for q in result["questions"]]
    assert any(q_id.startswith("q_mech_") for q_id in q_ids)


def test_electrical_student_personalization(monkeypatch):
    mock_profile = {
        "user_id": "user-ev-1",
        "target_role": "EV Technician",
        "degree": "ITI Electrician",
        "education_level": "Vocational",
        "skills": [{"skill_name": "EV Battery Technology", "proficiency": "intermediate"}],
        "career_interests": ["ev"],
    }
    monkeypatch.setattr(supabase_repository, "get_student_profile", lambda student_id: mock_profile)
    result = get_personalized_diagnostic_questions("user-ev-1")
    assert result["status"] == "success"
    assert result["domain"] == "electrical"
    assert len(result["questions"]) == 5
    q_ids = [q["id"] for q in result["questions"]]
    assert any(q_id.startswith("q_elec_") for q_id in q_ids)


def test_evaluate_assessment_returns_scores_and_knowledge_breakdown():
    submission_data = {
        "name": "Pratik Patil",
        "education": "B.Tech Computer Science",
        "career_goal": "AI Engineer",
        "district": "Pune",
        "current_skills": [
            {"skill_name": "Python", "proficiency": "advanced"},
            {"skill_name": "SQL", "proficiency": "intermediate"},
        ],
        "interests": ["ai_ml"],
        "quiz_answers": {
            "q_ai_rag": "b",
            "q_ai_overfit": "b",
            "q_sw_git": "a",
        },
    }

    result = evaluate_student_assessment(submission_data)

    assert "domain_readiness_score" in result
    assert "skill_proficiency_score" in result
    assert "knowledge_breakdown" in result
    assert result["domain_readiness_score"] == result["combined_readiness_score"]
    assert result["skill_proficiency_score"] == result["skill_match_pct"]

    breakdown = result["knowledge_breakdown"]
    assert "strong" in breakdown
    assert "moderate" in breakdown
    assert "weak" in breakdown
    assert "missing" in breakdown
    assert isinstance(breakdown["strong"], list)
    assert isinstance(breakdown["weak"], list)
    assert len(breakdown["strong"]) >= 1


def test_quiz_questions_endpoint_idor_protection(monkeypatch):
    from starlette.testclient import TestClient
    from app.main import app
    from app.core.security import create_access_token
    from app.db import save_user

    save_user({"id": "alice-user-456", "email": "alice@test.gov.in", "role": "STUDENT", "full_name": "Alice Student"})

    mock_profile = {
        "user_id": "victim-user-123",
        "target_role": "AI Engineer",
        "degree": "B.Tech AI",
        "education_level": "Undergraduate",
        "skills": [{"skill_name": "PyTorch", "proficiency": "advanced"}],
        "career_interests": ["ai_ml"],
    }
    monkeypatch.setattr(supabase_repository, "get_student_profile", lambda student_id: mock_profile if student_id == "victim-user-123" else None)

    with TestClient(app) as c:
        unauth_resp = c.get("/api/student/assessment/quiz-questions?student_id=victim-user-123")
        assert unauth_resp.status_code == 200
        unauth_data = unauth_resp.json()
        assert unauth_data["status"] == "unauthenticated"
        assert unauth_data["domain"] == "general"

        alice_token = create_access_token({"sub": "alice-user-456", "email": "alice@test.gov.in", "role": "STUDENT"})
        alice_resp = c.get(
            "/api/student/assessment/quiz-questions?student_id=victim-user-123",
            headers={"Authorization": f"Bearer {alice_token}"},
        )
        assert alice_resp.status_code == 200
        alice_data = alice_resp.json()
        assert alice_data["status"] == "profile_incomplete"


def test_learning_roadmap_endpoint_authorization_protection(monkeypatch):
    from starlette.testclient import TestClient
    from app.main import app
    from app.core.security import create_access_token
    from app.db import save_user

    save_user({"id": "bob-user-789", "email": "bob@test.gov.in", "role": "STUDENT", "full_name": "Bob Student"})
    save_user({"id": "victim-user-123", "email": "victim@test.gov.in", "role": "STUDENT", "full_name": "Victim Student"})

    mock_assessment = {
        "id": "ast-usr-victim",
        "user_id": "victim-user-123",
        "career_goal": "AI Engineer",
        "current_skills": [{"skill_id": "sk-001"}],
        "source": "USER_SUBMITTED",
        "is_demo": False,
    }
    monkeypatch.setattr(supabase_repository, "get_student_assessment", lambda aid: mock_assessment if aid == "victim-user-123" else None)
    monkeypatch.setattr(supabase_repository, "get_student_assessment_by_user", lambda uid: mock_assessment if uid == "victim-user-123" else None)
    monkeypatch.setattr(supabase_repository, "get_student_profile", lambda uid: None)

    with TestClient(app) as c:
        unauth_resp = c.get("/api/student/victim-user-123/roadmap")
        assert unauth_resp.status_code == 401

        bob_token = create_access_token({"sub": "bob-user-789", "email": "bob@test.gov.in", "role": "STUDENT"})
        bob_resp = c.get(
            "/api/student/victim-user-123/roadmap",
            headers={"Authorization": f"Bearer {bob_token}"},
        )
        assert bob_resp.status_code == 403

        victim_token = create_access_token({"sub": "victim-user-123", "email": "victim@test.gov.in", "role": "STUDENT"})
        victim_resp = c.get(
            "/api/student/victim-user-123/roadmap",
            headers={"Authorization": f"Bearer {victim_token}"},
        )
        assert victim_resp.status_code == 200
        assert victim_resp.json()["target_role"] == "AI Engineer"
