"""Tests for Phase 16: AI-Powered Career Recommendation & Skill-Gap Engine."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.career_recommendation_engine import (
    compute_career_recommendations,
    _get_validated_employer_demands,
    _match_skills,
)
from app.db import load_demo_data

load_demo_data()
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
    """Verify that only real VALIDATED employer submissions influence recommendations and DEMO_SYNTHETIC is excluded."""
    # 1. Baseline demo records (TCS, Quick Heal, etc.) must be strictly excluded from live recommendations
    validated_before = _get_validated_employer_demands()
    for d in validated_before:
        assert d.get("source") != "DEMO_SYNTHETIC"
        assert d.get("is_demo") is not True

    # 2. Add a real employer submission with validation_status=PENDING
    from app.db import save_employer_demand, update_employer_demand_status, delete_employer_demand
    real_demand = {
        "id": "ed-real-test-001",
        "company_name": "Authentic Tech India Ltd",
        "industry": "IT & Software",
        "district": "Pune",
        "job_role": "AI Engineer",
        "required_skills": ["Generative AI", "Python", "RAG"],
        "openings_count": 500,
        "source": "EMPLOYER_SUBMITTED",
        "is_demo": False,
        "validation_status": "PENDING",
    }
    save_employer_demand(real_demand)

    # 3. PENDING real demand must NOT appear in live validated demands or recommendations
    assert not any(d["id"] == "ed-real-test-001" for d in _get_validated_employer_demands())
    recs_pending = compute_career_recommendations("stu-001")
    top_ai = recs_pending["top_recommendation"]
    assert not any(e.get("id") == "ed-real-test-001" for e in top_ai.get("validated_employer_signals", []))

    # 4. Admin validates the real demand -> MUST now appear with full 500 openings
    update_employer_demand_status("ed-real-test-001", "VALIDATED", admin_notes="Verified real company credentials.")
    validated_after = _get_validated_employer_demands()
    assert any(d["id"] == "ed-real-test-001" for d in validated_after)

    recs_validated = compute_career_recommendations("stu-001")
    top_ai_val = recs_validated["top_recommendation"]
    matched_signal = next((e for e in top_ai_val.get("validated_employer_signals", []) if e.get("id") == "ed-real-test-001"), None)
    assert matched_signal is not None
    assert matched_signal["company_name"] == "Authentic Tech India Ltd"
    assert matched_signal["openings_count"] == 500
    assert matched_signal["validation_status"] == "VALIDATED"

    # 5. Admin rejects the real demand -> MUST immediately disappear
    update_employer_demand_status("ed-real-test-001", "REJECTED", admin_notes="Positions closed.")
    assert not any(d["id"] == "ed-real-test-001" for d in _get_validated_employer_demands())
    recs_rejected = compute_career_recommendations("stu-001")
    assert not any(e.get("id") == "ed-real-test-001" for e in recs_rejected["top_recommendation"].get("validated_employer_signals", []))

    # Clean up test record
    delete_employer_demand("ed-real-test-001")


def test_demo_synthetic_demands_never_leak_into_student_recommendations():
    """Verify that synthetic demo demands (TCS, Quick Heal, etc.) are excluded from student career recommendations."""
    recs = compute_career_recommendations("stu-001")
    for career in recs.get("recommended_careers", []):
        for sig in career.get("validated_employer_signals", []):
            assert sig.get("source") != "DEMO_SYNTHETIC"
            assert sig.get("is_demo") is not True



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
