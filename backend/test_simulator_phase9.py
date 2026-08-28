"""Test suite for Phase 9: Policy What-If Simulator."""
import pytest
from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_simulator_capacity_increase():
    """POST /api/simulator/whatif with capacity_increase scenario returns valid baseline+projection."""
    payload = {
        "scenario_type": "capacity_increase",
        "skill_category": "AI/ML",
        "district": "Pune",
        "capacity_change_pct": 30,
    }
    res = client.post("/api/simulator/whatif", json=payload)
    assert res.status_code == 200
    data = res.json()

    # Top-level structure
    assert data["label"] == "SIMULATED ESTIMATE"
    assert "disclaimer" in data
    assert "baseline" in data
    assert "projection" in data
    assert "available_categories" in data
    assert data["confidence_level"] == "medium"

    # Baseline must have core metrics
    bl = data["baseline"]
    assert "total_training_seats" in bl
    assert "avg_skill_gap_pct" in bl
    assert "placement_rate_pct" in bl
    assert "courses_count" in bl
    assert isinstance(bl["total_training_seats"], (int, float))

    # Projection for capacity_increase
    proj = data["projection"]
    assert "projected_total_seats" in proj
    assert "seats_added" in proj
    assert "projected_placement_rate_pct" in proj
    assert "projected_avg_gap_pct" in proj
    assert "trainers_required" in proj
    assert "equipment_units_required" in proj
    assert proj["projected_total_seats"] >= bl["total_training_seats"]
    assert proj["projected_avg_gap_pct"] <= bl["avg_skill_gap_pct"]


def test_simulator_curriculum_stale():
    """POST /api/simulator/whatif with curriculum_stale scenario shows degradation."""
    payload = {
        "scenario_type": "curriculum_stale",
        "stale_years": 3,
    }
    res = client.post("/api/simulator/whatif", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["label"] == "SIMULATED ESTIMATE"
    proj = data["projection"]
    bl = data["baseline"]

    # Stale curriculum should worsen gaps
    assert proj["projected_avg_gap_pct"] >= bl["avg_skill_gap_pct"]
    assert proj["projected_placement_rate_pct"] <= bl["placement_rate_pct"]
    assert "emerging_skills_at_risk" in proj
    assert isinstance(proj["emerging_skills_at_risk"], list)
    assert "industry_shortage_warning" in proj
    assert proj["stale_years"] == 3


def test_simulator_new_course():
    """POST /api/simulator/whatif with new_course scenario returns skill gap improvement."""
    payload = {
        "scenario_type": "new_course",
        "skill_category": "Electric Vehicles",
        "district": "Pune",
    }
    res = client.post("/api/simulator/whatif", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["label"] == "SIMULATED ESTIMATE"
    proj = data["projection"]
    bl = data["baseline"]

    assert "skills_addressed" in proj
    assert isinstance(proj["skills_addressed"], list)
    assert proj["projected_avg_gap_pct"] <= bl["avg_skill_gap_pct"]
    assert "trainers_required" in proj
    assert "new_course_seats" in proj


def test_simulator_unknown_type_fallback():
    """Unknown scenario_type should fallback gracefully (not crash)."""
    payload = {
        "scenario_type": "nonexistent_scenario",
        "capacity_change_pct": 20,
    }
    res = client.post("/api/simulator/whatif", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["label"] == "SIMULATED ESTIMATE"
    assert "baseline" in data
    assert "projection" in data


def test_simulator_categories_endpoint():
    """GET /api/simulator/categories returns a list of skill categories."""
    res = client.get("/api/simulator/categories")
    assert res.status_code == 200
    data = res.json()
    assert "categories" in data
    assert isinstance(data["categories"], list)
    assert len(data["categories"]) > 0
    # Known categories from demo data
    assert "AI/ML" in data["categories"]
    assert "Cloud" in data["categories"]
