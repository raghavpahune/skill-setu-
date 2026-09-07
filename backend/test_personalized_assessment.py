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
