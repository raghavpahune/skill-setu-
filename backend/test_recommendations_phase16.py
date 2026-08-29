"""Tests for Phase 16: AI-Powered Career Recommendation & Skill-Gap Engine."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.career_recommendation_engine import (
    compute_career_recommendations,
    _get_validated_employer_demands,
    _match_skills,
)

client = TestClient(app)


def test_compute_career_recommendations_valid_student():
    """Verify recommendation engine calculates all required metrics for a valid candidate."""
    data = compute_career_recommendations("stu-001")
    assert data["status"] == "success"
    assert data["student_id"] == "stu-001"
    assert data["candidate_name"] == "Aarav Patil"

    # Overall readiness
    readiness = data["overall_readiness"]
    assert "score" in readiness
    assert "level" in readiness
    assert "headline" in readiness
    assert readiness["score"] >= 0 and readiness["score"] <= 100

    # Current skills
    assert len(data["current_skill_profile"]) > 0

    # Recommended careers
    careers = data["recommended_careers"]
    assert len(careers) > 0
    top = data["top_recommendation"]
    assert top["role_name"] == "AI Engineer"
    assert "match_pct" in top
    assert "matching_skills" in top
    assert "missing_skills" in top
    assert "explanation_reasons" in top
    assert len(top["explanation_reasons"]) > 0

    # Validated employer demand signals
    assert "validated_employer_signals" in top
    for emp in top["validated_employer_signals"]:
        assert emp["validation_status"] == "VALIDATED"

    # Matched government opportunities
    assert "matched_government_opportunities" in top
    assert "personalized_roadmap" in data
    assert len(data["personalized_roadmap"]) > 0

    # Grounded explanation
    assert "ai_explanation" in data
    assert len(data["ai_explanation"]["summary"]) > 20

    # Provenance
    assert "data_provenance" in data
    assert data["data_provenance"]["employer_demand_source"] == "EMPLOYER_SUBMITTED_VALIDATED"


def test_recommendation_engine_invalid_student():
    """Verify error handling for non-existent student ID."""
    with pytest.raises(ValueError):
        compute_career_recommendations("non-existent-student-999")


def test_api_student_recommendations_endpoint():
    """Verify GET /api/student/recommendations/{student_id} endpoint."""
    res = client.get("/api/student/recommendations/stu-001")
    assert res.status_code == 200
    json_data = res.json()
    assert json_data["status"] == "success"
    assert json_data["student_id"] == "stu-001"
    assert len(json_data["recommended_careers"]) > 0

    # Test alias route /api/student/{student_id}/recommendations
    res_alias = client.get("/api/student/stu-001/recommendations")
    assert res_alias.status_code == 200
    assert res_alias.json()["status"] == "success"

    # Test 404 for invalid ID
    res_404 = client.get("/api/student/recommendations/invalid-id-xyz")
    assert res_404.status_code == 404


def test_strictly_validated_employer_demands():
    """Verify that only VALIDATED employer submissions influence recommendations."""
    validated = _get_validated_employer_demands()
    assert len(validated) > 0
    for d in validated:
        status = (d.get("validation_status") or d.get("status") or "").upper()
        assert status in ("VALIDATED", "APPROVED") or d.get("status") == "active"


def test_skill_matching_logic():
    """Verify deterministic skill matching and gap calculation."""
    student_skills = [
        {"skill_name": "Python", "proficiency": "advanced"},
        {"skill_name": "SQL", "proficiency": "intermediate"},
    ]
    required = ["Python", "SQL", "Machine Learning", "Tableau"]

    matched, missing, match_pct = _match_skills(student_skills, required)
    assert "Python" in matched
    assert "SQL" in matched
    assert "Machine Learning" in missing
    assert "Tableau" in missing
    assert match_pct > 0 and match_pct < 100


def test_explain_ai_endpoint_and_offline_fallback():
    """Verify POST /api/student/recommendations/{student_id}/explain-ai endpoint and fallback."""
    res = client.post(
        "/api/student/recommendations/stu-001/explain-ai",
        json={"prompt": "Explain in simple terms why AI Engineer is recommended."}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "ai_explanation" in data
    assert len(data["ai_explanation"]) > 20
    assert "recommendation_summary" in data


def test_different_candidate_profiles_yield_distinct_rankings():
    """Verify different student profiles receive tailored, distinct career recommendations."""
    res_ai = client.get("/api/student/recommendations/stu-001")
    res_ev = client.get("/api/student/recommendations/stu-003")

    assert res_ai.status_code == 200
    assert res_ev.status_code == 200

    top_ai = res_ai.json()["top_recommendation"]["role_name"]
    top_ev = res_ev.json()["top_recommendation"]["role_name"]

    assert top_ai == "AI Engineer"
    assert top_ev == "EV Technician"
