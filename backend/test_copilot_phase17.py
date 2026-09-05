"""Tests for Phase 17: AI Career Copilot and Explainability Layer."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.career_recommendation_engine import compute_career_recommendations

client = TestClient(app)


@pytest.fixture(autouse=True)
def enable_demo_mode_for_phase17(monkeypatch):
    monkeypatch.setenv("SKILLSETU_DATA_MODE", "demo")


def test_copilot_ask_with_student_id_context():
    """Verify copilot grounds response in student recommendation when student_id is provided."""
    res = client.post(
        "/api/copilot/ask",
        json={
            "question": "Why is my target career recommended for me?",
            "role": "student",
            "student_id": "stu-001",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert len(data["answer"]) > 50
    assert data["role"] == "student"
    assert data["student_id"] == "stu-001"
    assert data["data_grounded"] is True
    assert "provenance_label" in data

    # Grounded content assertions
    answer = data["answer"]
    assert "AI Engineer" in answer or "Aarav" in answer or "Career Recommendation" in answer
    assert "Grounded" in data["provenance_label"] or "Gemini" in data["provenance_label"]


def test_copilot_explain_career_endpoint():
    """Verify POST /api/copilot/explain-career endpoint."""
    res = client.post(
        "/api/copilot/explain-career",
        json={
            "student_id": "stu-001",
            "question": "Explain my validated employer demand signals and government opportunities.",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert data["student_id"] == "stu-001"
    assert data["data_grounded"] is True


def test_deterministic_engine_truth_preservation():
    """Verify that Copilot explainability reflects exact deterministic metrics without distortion."""
    deterministic = compute_career_recommendations("stu-001")
    top_role = deterministic["top_recommendation"]["role_name"]
    match_pct = deterministic["top_recommendation"]["match_pct"]
    readiness_score = deterministic["overall_readiness"]["score"]

    res = client.post(
        "/api/copilot/explain-career",
        json={"student_id": "stu-001"},
    )
    assert res.status_code == 200
    answer = res.json()["answer"]

    # Verify key deterministic anchor metrics are referenced
    assert top_role in answer
    assert f"{match_pct}%" in answer or str(match_pct) in answer
    assert f"{readiness_score}%" in answer or str(readiness_score) in answer


def test_copilot_fallback_when_gemini_unavailable():
    """Verify rule-based offline provider generates rich, truthful response when live LLM is disabled."""
    from ai.demo_provider import DemoProvider
    import asyncio

    provider = DemoProvider()
    from ai.copilot import _build_context
    context = _build_context("student", "Explain my career roadmap", district="Pune", student_id="stu-001")

    answer = asyncio.run(provider.generate("Explain my career roadmap", context))
    assert len(answer) > 100
    assert "Career Recommendation" in answer or "AI Engineer" in answer
    assert "Provenance Note" in answer


def test_copilot_different_students_distinct_grounding():
    """Verify copilot provides distinct, tailored advice for different candidate profiles."""
    res_ai = client.post(
        "/api/copilot/explain-career",
        json={"student_id": "stu-001"},
    )
    res_ev = client.post(
        "/api/copilot/explain-career",
        json={"student_id": "stu-003"},
    )

    assert res_ai.status_code == 200
    assert res_ev.status_code == 200

    ans_ai = res_ai.json()["answer"]
    ans_ev = res_ev.json()["answer"]

    assert "AI Engineer" in ans_ai or "Aarav" in ans_ai
    assert "EV Technician" in ans_ev or "Rohan" in ans_ev
