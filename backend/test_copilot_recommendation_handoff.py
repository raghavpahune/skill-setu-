"""Tests for Context-Aware Ask Copilot from Student Recommendations (Phase 18)."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_copilot_recommendation_handoff_generative_ai():
    """Verify recommendation handoff for Generative AI produces grounded, structured response."""
    payload = {
        "question": (
            "Explain why I should learn Generative AI based on my SkillSetu profile "
            "and current Maharashtra labour-market intelligence. My target role is AI Engineer. "
            "Show the relevant demand signals, required competencies, my missing prerequisites, "
            "relevant SkillSetu courses/training, and a practical learning path."
        ),
        "role": "student",
        "student_id": "stu-001",
        "context_data": {
            "topic": "Generative AI",
            "recommendation_title": "Why Learn Generative AI?",
            "target_role": "AI Engineer",
            "student_name": "Aarav Sharma",
            "student_id": "stu-001",
            "missing_prerequisites": ["Generative AI"],
            "source": "SkillSetu Grounded Labour Intelligence",
        },
    }

    res = client.post("/api/copilot/ask", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    answer = data["answer"]

    # 1. Why skill matters & target role alignment
    assert "AI Engineer" in answer
    assert "Generative AI" in answer

    # 2. Labour-market demand & signals
    assert "demand" in answer.lower() or "vacancies" in answer.lower()
    assert "Maharashtra" in answer or "Pune" in answer

    # 3. Candidate alignment & missing prerequisites
    assert "Missing Prerequisite" in answer or "Prerequisite" in answer

    # 4. Relevant accredited courses (COEP Technological University / real course)
    assert "COEP" in answer or "Generative AI & LLM Applications" in answer

    # 5. Practical step-by-step learning sequence
    assert "Learning Path" in answer or "Step" in answer or "Prerequisites" in answer

    # 6. Actionable next step
    assert "Next Action" in answer or "roadmap" in answer.lower() or "Dashboard" in answer

    # Data grounding assertions
    assert data["data_grounded"] is True


def test_copilot_recommendation_handoff_dynamic_second_skill():
    """Verify recommendation handoff is dynamic for other skills (e.g. Python for Data Analyst)."""
    payload = {
        "question": (
            "Explain why I should learn Python based on my SkillSetu profile "
            "and current Maharashtra labour-market intelligence. My target role is Data Analyst. "
            "Show the relevant demand signals, required competencies, my missing prerequisites, "
            "relevant SkillSetu courses/training, and a practical learning path."
        ),
        "role": "student",
        "student_id": "stu-002",
        "context_data": {
            "topic": "Python",
            "recommendation_title": "Why Learn Python?",
            "target_role": "Data Analyst",
            "student_id": "stu-002",
            "source": "SkillSetu Grounded Labour Intelligence",
        },
    }

    res = client.post("/api/copilot/ask", json=payload)
    assert res.status_code == 200
    answer = res.json()["answer"]

    assert "Python" in answer
    assert "Data Analyst" in answer
    assert "Maharashtra" in answer or "Pune" in answer or "Mumbai" in answer


def test_copilot_no_fake_course_when_none_exist():
    """Verify that when a skill has no accredited courses, Copilot truthfully states none found."""
    payload = {
        "question": "Why should I learn Solidity for my target career?",
        "role": "student",
        "student_id": "stu-001",
        "context_data": {
            "topic": "Solidity",
            "recommendation_title": "Why Learn Solidity?",
            "target_role": "Blockchain Developer",
        },
    }

    res = client.post("/api/copilot/ask", json=payload)
    assert res.status_code == 200
    answer = res.json()["answer"]
    # Should cleanly state unindexed / insufficient records / no state-accredited course
    assert "No verified" in answer or "No accredited" in answer or "no accredited" in answer.lower() or "not contain sufficient" in answer


def test_direct_copilot_still_works_without_recommendation_context():
    """Direct Copilot inquiry without recommendation context continues to work as expected."""
    res = client.post(
        "/api/copilot/ask",
        json={"question": "Tell me about requirement for Python developer in Pune", "role": "student"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "Python" in data["answer"]
    assert data["role"] == "student"
