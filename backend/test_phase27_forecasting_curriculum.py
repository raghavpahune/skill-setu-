"""Phase 27 Automated Test Suite — Multi-Horizon Forecasting & Curriculum Modernization."""
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.services.forecast_engine import (
    compute_multi_horizon_forecasts,
    get_skill_forecast_trajectory,
    generate_future_skills_radar,
)
from app.services.curriculum_engine import (
    audit_all_courses,
    get_course_modernization_blueprint,
)


@pytest.fixture
def client():
    return TestClient(app)


# =========================================================================
# 1. Multi-Horizon Forecasting Service Tests
# =========================================================================

def test_compute_multi_horizon_forecasts():
    forecasts = compute_multi_horizon_forecasts()
    assert len(forecasts) >= 10
    for fc in forecasts:
        assert "skill_id" in fc
        assert "skill_name" in fc
        assert "current_demand_score" in fc
        assert "projected_6m" in fc
        assert "projected_12m" in fc
        assert "projected_24m" in fc
        assert fc["trend"] in ("RISING", "EMERGING", "STABLE", "DECLINING")
        assert 0 <= fc["confidence_score"] <= 100
        assert len(fc["key_drivers"]) >= 1
        assert "6_months" in fc["horizon_breakdown"]
        assert "12_months" in fc["horizon_breakdown"]
        assert "24_months" in fc["horizon_breakdown"]


def test_get_skill_forecast_trajectory():
    fc = get_skill_forecast_trajectory("sk-001")
    assert fc is not None
    assert fc["skill_id"] == "sk-001"
    assert fc["projected_24m"] >= 0

    fc_invalid = get_skill_forecast_trajectory("sk-non-existent-999")
    assert fc_invalid is None


def test_generate_future_skills_radar():
    radar = generate_future_skills_radar()
    assert radar["status"] == "success"
    assert "rising_skills" in radar
    assert "emerging_skills" in radar
    assert "stable_skills" in radar
    assert "domain_growth_matrix" in radar
    assert len(radar["domain_growth_matrix"]) >= 1


# =========================================================================
# 2. Forecasting API Endpoints
# =========================================================================

def test_api_forecast_endpoints(client):
    # Standard list
    res = client.get("/api/forecast")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0

    # Filter by horizon
    res_24m = client.get("/api/forecast?horizon=24m")
    assert res_24m.status_code == 200
    data_24m = res_24m.json()
    assert data_24m[0]["projected_24m"] >= data_24m[-1]["projected_24m"]

    # Filter by trend
    res_rising = client.get("/api/forecast?trend=RISING")
    assert res_rising.status_code == 200
    data_rising = res_rising.json()
    for item in data_rising:
        assert item["trend"] == "RISING"

    # Radar
    res_radar = client.get("/api/forecast/radar")
    assert res_radar.status_code == 200
    assert res_radar.json()["status"] == "success"

    # Single skill
    res_single = client.get("/api/forecast/skill/sk-001")
    assert res_single.status_code == 200
    assert len(res_single.json()) == 1


# =========================================================================
# 3. Course Obsolescence & Curriculum Modernization Engine Tests
# =========================================================================

def test_audit_all_courses():
    courses = audit_all_courses()
    assert len(courses) >= 5
    for c in courses:
        assert "course_id" in c
        assert "course_name" in c
        assert "health_score" in c
        assert "placement_rate" in c
        assert "modernity_score" in c
        assert c["obsolescence_risk"] in ("CRITICAL_OBSOLETE", "HIGH_RISK", "MODERATE", "HEALTHY")
        assert "OVERSUPPLY" in c["oversupply_status"] or c["oversupply_status"] == "BALANCED"
        assert "equipment_requirements" in c
        assert c["total_equipment_budget_inr"] > 0
        assert len(c["trainer_upskilling"]) >= 1


def test_get_course_modernization_blueprint():
    # Valid course
    blueprint = get_course_modernization_blueprint("cr-001")
    assert blueprint is not None
    assert blueprint["status"] == "success"
    assert blueprint["course_id"] == "cr-001"
    assert "health_summary" in blueprint
    assert "modernization_blueprint" in blueprint
    mb = blueprint["modernization_blueprint"]
    assert len(mb["action_plan"]) >= 2
    assert len(mb["equipment_requirements"]) >= 1
    assert mb["total_equipment_budget_inr"] > 0

    # Nonexistent course
    invalid = get_course_modernization_blueprint("cr-invalid-999")
    assert invalid is None


# =========================================================================
# 4. Curriculum Modernization API Endpoints
# =========================================================================

def test_api_curriculum_endpoints(client):
    # Audit list
    res = client.get("/api/curriculum/audit")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["total_courses_audited"] >= 5

    # Filter audit by district
    res_pune = client.get("/api/curriculum/audit?district=Pune")
    assert res_pune.status_code == 200
    assert all("pune" in c["district"].lower() for c in res_pune.json()["courses"])

    # Curriculum summary KPIs
    res_summary = client.get("/api/curriculum/summary")
    assert res_summary.status_code == 200
    summary = res_summary.json()
    assert summary["total_courses"] >= 5
    assert summary["avg_health_score"] > 0
    assert summary["total_equipment_budget_estimate_inr"] > 0

    # Modernization blueprint
    res_bp = client.get("/api/curriculum/recommendations/cr-001")
    assert res_bp.status_code == 200
    assert res_bp.json()["course_id"] == "cr-001"

    # Nonexistent course 404
    res_404 = client.get("/api/curriculum/recommendations/cr-nonexistent")
    assert res_404.status_code == 404
