"""Tests verifying all 8 CodeRabbit PR #1 hardening fixes and zero raw exception leakage."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.core.security import create_access_token, verify_password
from app.db import get_demo, get_user_by_email, save_user
from app.services.career_recommendation_engine import compute_career_recommendations
from app.services.student_service import get_skill_explainability

client = TestClient(app)

STUDENT1_TOKEN = create_access_token({"sub": "usr-student-001", "email": "student@skillsetu.gov.in", "role": "STUDENT"})
STUDENT2_TOKEN = create_access_token({"sub": "usr-student-002", "email": "student2@skillsetu.gov.in", "role": "STUDENT"})
AUTH_HEADERS_S1 = {"Authorization": f"Bearer {STUDENT1_TOKEN}"}
AUTH_HEADERS_S2 = {"Authorization": f"Bearer {STUDENT2_TOKEN}"}


# ============================================================================
# CodeRabbit Finding #1: Skill Classification
# Unclassified skills must not automatically become missing.
# ============================================================================
@pytest.mark.anyio
async def test_finding_1_unclassified_skill_not_automatically_missing():
    from ai.copilot import handle_question
    # Aarav Sharma (stu-001) has target role AI Engineer.
    # An unrelated skill like "Pottery Making" or "Culinary Arts" is neither in matching_skills,
    # missing_skills, roadmap_skills, nor AI Engineer benchmark.
    res = await handle_question(
        question="Tell me about Pottery",
        role="student",
        student_id="stu-001",
        context_data={"queried_skill": {"name": "Pottery Making"}},
    )
    # The student recommendation context must NOT mark Pottery Making as missing
    srec = res.get("context_data", {}).get("student_recommendation_context")
    if srec:
        assert srec.get("is_queried_skill_missing") is False


# ============================================================================
# CodeRabbit Finding #2: Copilot Input Validation
# Malformed context_data must return HTTP 422, not HTTP 500.
# ============================================================================
def test_finding_2_malformed_context_data_returns_422():
    # 1. target_role passed as an integer instead of string
    res1 = client.post("/api/copilot/ask", json={
        "question": "Why learn this skill?",
        "role": "student",
        "context_data": {
            "target_role": 12345,  # Invalid type: must be StrictStr
        }
    })
    assert res1.status_code == 422

    # 2. missing_prerequisites passed as a string instead of list of strings
    res2 = client.post("/api/copilot/ask", json={
        "question": "Why learn this skill?",
        "role": "student",
        "context_data": {
            "missing_prerequisites": "Not a list",  # Invalid type
        }
    })
    assert res2.status_code == 422


# ============================================================================
# CodeRabbit Finding #3: No Authorization Solely Based on ID Prefix
# Actual record classification + ownership must control access.
# ============================================================================
def test_finding_3_prefix_alone_does_not_bypass_authorization():
    # Create a private assessment record whose ID happens to start with "stu-"
    private_record = {
        "id": "stu-private-security-test-999",
        "user_id": "usr-student-001",
        "user_email": "student@skillsetu.gov.in",
        "name": "Secret Candidate",
        "source": "USER_SUBMITTED",
        "is_demo": False,
        "career_goal": "AI Engineer",
        "skills": [{"skill_name": "Python", "proficiency": "advanced"}],
    }

    with patch("app.repositories.supabase_repository.get_student_assessment", return_value=private_record):
        # Unauthenticated request must receive 401, NOT 200, despite starting with "stu-"
        res_unauth = client.get("/api/student/recommendations/stu-private-security-test-999")
        assert res_unauth.status_code == 401

        # Unrelated student must receive 403 Forbidden
        res_other = client.get(
            "/api/student/recommendations/stu-private-security-test-999",
            headers=AUTH_HEADERS_S2,
        )
        assert res_other.status_code == 403

        # Legitimate owner receives 200
        res_owner = client.get(
            "/api/student/recommendations/stu-private-security-test-999",
            headers=AUTH_HEADERS_S1,
        )
        assert res_owner.status_code == 200


# ============================================================================
# CodeRabbit Finding #4: Raw Database Exception Leakage
# Responses must never leak internal SQL, table names, or raw exception strings.
# ============================================================================
def test_finding_4_zero_raw_exception_leakage_on_database_failure():
    secret_error_msg = "SECRET_DB_EXCEPTION_123_CONNECTION_DEAD_FATAL"

    def mock_failing_query(*args, **kwargs):
        raise RuntimeError(secret_error_msg)

    with patch("app.repositories.supabase_repository.get_student_assessment", side_effect=mock_failing_query), \
         patch("app.repositories.supabase_repository.get_student_assessment_by_user", side_effect=mock_failing_query):

        # Test student assessment endpoint
        res = client.get("/api/student/assessment/non_demo_student_id_xyz", headers=AUTH_HEADERS_S1)
        assert res.status_code == 500
        body = res.text
        assert secret_error_msg not in body
        assert "Database query failed" in res.json()["detail"]

        # Test passport endpoint
        res_passport = client.get("/api/student/me/passport", headers=AUTH_HEADERS_S1)
        assert res_passport.status_code == 500
        assert secret_error_msg not in res_passport.text
        assert "Database query failed" in res_passport.json()["detail"]


# ============================================================================
# CodeRabbit Finding #5: Career Forecast Provenance & Strict Data Authority
# Real-user Supabase forecast failure must NOT silently become demo forecast.
# ============================================================================
def test_finding_5_real_user_forecast_failure_raises_controlled_error():
    real_profile = {
        "id": "usr-student-real-prod-1",
        "user_id": "usr-student-real-prod-1",
        "source": "USER_SUBMITTED",
        "is_demo": False,
        "name": "Production Candidate",
        "career_goal": "AI Engineer",
        "current_skills": [{"skill_name": "Python", "proficiency": "intermediate"}],
    }

    def mock_failing_forecasts(*args, **kwargs):
        raise RuntimeError("Supabase connection lost")

    with patch("app.repositories.supabase_repository.get_student_assessment", return_value=real_profile), \
         patch("app.repositories.supabase_repository.get_student_assessment_by_user", return_value=real_profile), \
         patch("app.repositories.supabase_repository.get_student_profile", return_value=real_profile), \
         patch("app.repositories.supabase_repository.list_skill_forecasts", side_effect=mock_failing_forecasts):

        # For a real user, failing Supabase forecasts must raise RuntimeError, NOT silently use demo forecasts
        with pytest.raises(RuntimeError) as exc_info:
            compute_career_recommendations("usr-student-real-prod-1")
        assert "Database error fetching skill forecasts" in str(exc_info.value)


def test_finding_5_roadmap_steps_include_forecast_provenance():
    # For demo candidate, verify roadmap steps include forecast_source and forecast_verified
    rec = compute_career_recommendations("stu-001")
    roadmap = rec.get("personalized_roadmap", [])
    assert len(roadmap) > 0
    for step in roadmap:
        assert "forecast_source" in step
        assert "forecast_verified" in step


# ============================================================================
# CodeRabbit Finding #6: Student Forecast Verified Flag
# Demo forecasts must NEVER be returned as verified=True.
# ============================================================================
def test_finding_6_demo_forecast_is_never_verified_true():
    # Force list_skill_forecasts to fail so it falls back to demo forecasts
    with patch("app.repositories.supabase_repository.list_skill_forecasts", side_effect=RuntimeError("Unavailable")):
        result = get_skill_explainability("Generative AI", student_id="stu-001")
        assert result.get("data_available") is not False
        dim_fc = result.get("explainability", {}).get("dimension_2_future_forecast", {})
        assert dim_fc.get("verified") is False
        assert dim_fc.get("forecast_source") == "DEMO_SYNTHETIC"


# ============================================================================
# CodeRabbit Finding #7: Copilot Tests Deterministically Use DemoProvider
# ============================================================================
def test_finding_7_copilot_uses_demo_provider():
    from ai.copilot import _get_provider
    from ai.demo_provider import DemoProvider
    provider = _get_provider()
    # When GEMINI_API_KEY is not configured or in test mode, DemoProvider is returned
    assert isinstance(provider, DemoProvider) or provider.__class__.__name__ == "DemoProvider"


# ============================================================================
# CodeRabbit Finding #8: User Password Hashes
# usr-student-002 must have a valid bcrypt hash and verify against Password@123.
# ============================================================================
def test_finding_8_usr_student_002_has_valid_bcrypt_hash():
    user = get_user_by_email("student2@skillsetu.gov.in")
    assert user is not None
    assert user.get("id") == "usr-student-002"
    hashed = user.get("hashed_password")
    assert hashed is not None
    assert hashed != "demo_password_hash"
    assert hashed.startswith(("$2b$", "$2a$"))
    # Verify password verification succeeds
    assert verify_password("Password@123", hashed) is True
