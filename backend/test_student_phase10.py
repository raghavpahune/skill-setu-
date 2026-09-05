"""Test suite for Phase 10: Student Personalized Industry Alerts & Skill Explainability Hub."""
import pytest
from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def enable_demo_mode_for_phase10(monkeypatch):
    monkeypatch.setenv("SKILLSETU_DATA_MODE", "demo")


def test_alert_domains_endpoint():
    """GET /api/student/alert-domains returns all 7 spec-mandated domains."""
    res = client.get("/api/student/alert-domains")
    assert res.status_code == 200
    data = res.json()
    assert "domains" in data
    domains = data["domains"]
    assert len(domains) >= 7

    domain_ids = {d["id"] for d in domains}
    expected_ids = {"ai_ml", "data_science", "cloud", "cybersecurity", "robotics", "ev", "iot"}
    assert expected_ids.issubset(domain_ids)

    for d in domains:
        assert "id" in d
        assert "name" in d
        assert "icon" in d
        assert "description" in d


def test_personalized_industry_alerts_all():
    """GET /api/student/industry-alerts returns complete grounded alert feed."""
    res = client.get("/api/student/industry-alerts")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "alerts" in data
    assert len(data["alerts"]) > 0

    first_alert = data["alerts"][0]
    assert "domain_id" in first_alert
    assert "domain_name" in first_alert
    assert "primary_signal" in first_alert
    assert "career_impact" in first_alert
    assert "job_demand_signal" in first_alert
    assert "affected_skills" in first_alert
    assert "actionable_next_steps" in first_alert
    assert "related_courses" in first_alert

    # Career impact structure
    impact = first_alert["career_impact"]
    assert "level" in impact
    assert "score_out_of_10" in impact
    assert isinstance(impact["score_out_of_10"], int)

    # Job demand signal structure
    demand = first_alert["job_demand_signal"]
    assert "active_vacancies_count" in demand
    assert "demand_share_pct" in demand
    assert "hiring_trend" in demand


def test_personalized_industry_alerts_domain_filtering():
    """GET /api/student/industry-alerts?domain=ev returns EV-specific telemetry."""
    res = client.get("/api/student/industry-alerts?domain=ev")
    assert res.status_code == 200
    data = res.json()
    assert data["selected_domain"] == "ev"
    assert len(data["alerts"]) == 1
    ev_alert = data["alerts"][0]
    assert ev_alert["domain_id"] == "ev"
    assert "Electric Vehicles" in ev_alert["domain_name"]
    assert any("EV" in s["name"] or "Battery" in s["name"] for s in ev_alert["affected_skills"])


def test_personalized_industry_alerts_unknown_domain_fallback():
    """Unknown domain query falls back gracefully to default feed without 500 error."""
    res = client.get("/api/student/industry-alerts?domain=nonexistent_quantum_domain")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert len(data["alerts"]) > 0


def test_personalized_industry_alerts_student_context():
    """Passing student_id returns tailored skills to strengthen."""
    res = client.get("/api/student/industry-alerts?domain=ai_ml&student_id=stu-001")
    assert res.status_code == 200
    data = res.json()
    assert data["student_id"] == "stu-001"
    ai_alert = data["alerts"][0]
    assert "skills_to_strengthen" in ai_alert
    assert isinstance(ai_alert["skills_to_strengthen"], list)


def test_skill_explainability_by_id():
    """GET /api/student/skill-explainability/{id} returns 5-dimension grounded evidence."""
    res = client.get("/api/student/skill-explainability/sk-006")  # RAG
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["data_available"] is True
    assert data["skill"]["id"] == "sk-006"
    assert data["skill"]["name"] == "RAG"

    expl = data["explainability"]
    # Dimension 1: Demand Surge
    assert "dimension_1_demand_surge" in expl
    d1 = expl["dimension_1_demand_surge"]
    assert d1["verified"] is True
    assert "demand_pct" in d1
    assert "active_vacancies_count" in d1
    assert "top_hiring_districts" in d1

    # Dimension 2: Future Forecast
    assert "dimension_2_future_forecast" in expl
    d2 = expl["dimension_2_future_forecast"]
    assert "future_demand" in d2
    assert "trend" in d2

    # Dimension 3: Employer Consensus
    assert "dimension_3_employer_consensus" in expl
    d3 = expl["dimension_3_employer_consensus"]
    assert "demand_rating" in d3
    assert "avg_days_to_fill" in d3

    # Dimension 4: Curriculum Deficit
    assert "dimension_4_curriculum_deficit" in expl
    d4 = expl["dimension_4_curriculum_deficit"]
    assert "curriculum_coverage_pct" in d4
    assert "skill_gap_pct" in d4
    assert "teaching_courses" in d4

    # Dimension 5: Academic Rationale
    assert "dimension_5_academic_rationale" in expl
    d5 = expl["dimension_5_academic_rationale"]
    assert "formal_statement" in d5
    assert len(d5["formal_statement"]) > 20


def test_skill_explainability_by_name_and_synonym():
    """Explainability resolves case-insensitive names and synonyms."""
    # By name
    res_name = client.get("/api/student/skill-explainability/Python")
    assert res_name.status_code == 200
    assert res_name.json()["skill"]["name"] == "Python"

    # By synonym
    res_syn = client.get("/api/student/skill-explainability/Generative%20Artificial%20Intelligence")
    assert res_syn.status_code == 200
    assert res_syn.json()["skill"]["name"] == "Generative AI"


def test_skill_explainability_student_alignment():
    """Explainability includes student profile alignment when student_id is provided."""
    res = client.get("/api/student/skill-explainability/sk-006?student_id=stu-001")
    assert res.status_code == 200
    data = res.json()
    assert "student_alignment" in data
    align = data["student_alignment"]
    assert align["target_role"] == "AI Engineer"
    assert "status_label" in align


def test_skill_explainability_unknown_skill():
    """Non-existent skill returns transparent error and data_available: false."""
    res = client.get("/api/student/skill-explainability/unknown_nonexistent_skill_xyz")
    assert res.status_code == 200
    data = res.json()
    assert data["data_available"] is False
    assert "error" in data
