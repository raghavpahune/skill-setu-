"""Regression tests verifying strict isolation of demo employer demands from live student recommendations."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.career_recommendation_engine import (
    compute_career_recommendations,
    _get_validated_employer_demands,
    _is_live_employer_demand,
)
from app.db import (
    init_db,
    save_employer_demand,
    update_employer_demand_status,
    delete_employer_demand,
    get_demo,
)

init_db()
client = TestClient(app)


def test_is_live_employer_demand_predicate():
    """Unit test for _is_live_employer_demand helper covering all provenance variations."""
    # 1. Synthetic demo demands
    assert not _is_live_employer_demand({"is_demo": True, "source": "DEMO_SYNTHETIC"})
    assert not _is_live_employer_demand({"source": "DEMO_SYNTHETIC"})
    assert not _is_live_employer_demand({"source": "DEMO"})
    assert not _is_live_employer_demand({"is_demo": True, "source": "EMPLOYER_SUBMITTED"})
    assert not _is_live_employer_demand(None)
    assert not _is_live_employer_demand({})

    # 2. Genuine live demands
    assert _is_live_employer_demand({"source": "EMPLOYER_SUBMITTED", "is_demo": False})
    assert _is_live_employer_demand({"source": "USER_SUBMITTED", "is_demo": False})
    assert _is_live_employer_demand({"source": "FIRST_PARTY", "is_demo": False})
    assert _is_live_employer_demand({"company_name": "Acme", "is_demo": False})


def test_demo_synthetic_demands_excluded_from_validated_list():
    """Verify that seeded demo demands (ed-001 TCS, ed-004 Quick Heal, etc.) are excluded from _get_validated_employer_demands."""
    all_demands = get_demo("employer_demands")
    demo_demands = [d for d in all_demands if d.get("source") == "DEMO_SYNTHETIC" or d.get("is_demo") is True]
    assert len(demo_demands) > 0, "Demo demands baseline fixture should exist in database cache"

    validated_live_demands = _get_validated_employer_demands()
    for d in validated_live_demands:
        assert d.get("source") != "DEMO_SYNTHETIC"
        assert d.get("is_demo") is not True
        assert d["id"] not in {demo["id"] for demo in demo_demands}


def test_real_demand_lifecycle_and_500_openings_visibility():
    """Verify that a real 500-opening employer submission follows the exact PENDING -> VALIDATED -> REJECTED lifecycle."""
    demand_id = "ed-prod-scale-500"
    real_demand_payload = {
        "id": demand_id,
        "company_name": "Bharat Renewable Robotics Ltd",
        "industry": "Renewable Energy",
        "district": "Pune",
        "job_role": "EV Battery Management System (BMS) Calibration Specialist",
        "required_skills": ["EV Battery Technology", "Battery Management (BMS)", "Motor Control", "CAN Bus"],
        "openings_count": 500,
        "positions_count": 500,
        "source": "EMPLOYER_SUBMITTED",
        "is_demo": False,
        "validation_status": "PENDING",
    }
    save_employer_demand(real_demand_payload)

    try:
        # CASE A: PENDING -> must NOT appear in live recommendations
        assert not any(d["id"] == demand_id for d in _get_validated_employer_demands())
        recs_pending = compute_career_recommendations("stu-003")  # EV student
        ev_role_pending = next((c for c in recs_pending["recommended_careers"] if c["role_name"] == "EV Technician"), None)
        assert ev_role_pending is not None
        assert not any(s.get("id") == demand_id for s in ev_role_pending.get("validated_employer_signals", []))

        # CASE B: VALIDATED -> MUST appear with 500 openings
        update_employer_demand_status(demand_id, "VALIDATED", admin_notes="500 openings verified on-site.")
        assert any(d["id"] == demand_id for d in _get_validated_employer_demands())
        recs_val = compute_career_recommendations("stu-003")
        ev_role_val = next((c for c in recs_val["recommended_careers"] if c["role_name"] == "EV Technician"), None)
        assert ev_role_val is not None
        signal = next((s for s in ev_role_val.get("validated_employer_signals", []) if s.get("id") == demand_id), None)
        assert signal is not None
        assert signal["company_name"] == "Bharat Renewable Robotics Ltd"
        assert signal["openings_count"] == 500
        assert signal["validation_status"] == "VALIDATED"

        # CASE C: REJECTED -> MUST NOT appear
        update_employer_demand_status(demand_id, "REJECTED", admin_notes="Recruitment drive cancelled.")
        assert not any(d["id"] == demand_id for d in _get_validated_employer_demands())
        recs_rej = compute_career_recommendations("stu-003")
        ev_role_rej = next((c for c in recs_rej["recommended_careers"] if c["role_name"] == "EV Technician"), None)
        assert not any(s.get("id") == demand_id for s in ev_role_rej.get("validated_employer_signals", []))
    finally:
        delete_employer_demand(demand_id)


def test_live_recommendation_api_zero_synthetic_leakage():
    """Verify that calling GET /api/student/recommendations/stu-001 yields NO synthetic demo employer openings."""
    res = client.get("/api/student/recommendations/stu-001")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"

    for career in data.get("recommended_careers", []):
        for signal in career.get("validated_employer_signals", []):
            assert signal.get("source") != "DEMO_SYNTHETIC"
            assert signal.get("is_demo") is not True
            # Assert known demo company IDs are never leaked
            assert signal.get("id") not in ("ed-001", "ed-002", "ed-003", "ed-004", "ed-005", "ed-006")
