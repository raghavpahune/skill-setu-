"""Tests for Phase 28: District-Level Workforce Planning Intelligence (§13) & Platform Success Metrics (§33)."""
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.services.district_service import (
    get_all_districts,
    get_district_plan,
    get_platform_metrics_summary,
)

client = TestClient(app)


def test_get_all_districts():
    """Verify listing all districts returns valid entries with job and course counts."""
    districts = get_all_districts()
    assert isinstance(districts, list)
    assert len(districts) > 0
    pune_entry = next((d for d in districts if d["name"].lower() == "pune"), None)
    assert pune_entry is not None
    assert "job_count" in pune_entry
    assert "course_count" in pune_entry
    assert pune_entry["job_count"] > 0


def test_get_district_plan_pune_all_11_spec_fields():
    """Verify get_district_plan for Pune returns all 11 fields required by Section 13."""
    plan = get_district_plan("Pune")
    assert plan["district"] == "Pune"
    
    # 1. Top 5 Demanded Roles
    assert "top_roles" in plan
    assert isinstance(plan["top_roles"], list)
    assert len(plan["top_roles"]) <= 5
    assert len(plan["top_roles"]) > 0
    assert "role" in plan["top_roles"][0]
    assert "count" in plan["top_roles"][0]

    # 2. Top Skills
    assert "top_skills" in plan
    assert isinstance(plan["top_skills"], list)
    assert len(plan["top_skills"]) > 0
    assert "skill_name" in plan["top_skills"][0]
    assert "demand_count" in plan["top_skills"][0]

    # 3. Skill Gaps
    assert "skill_gaps" in plan
    assert isinstance(plan["skill_gaps"], list)
    assert len(plan["skill_gaps"]) > 0

    # 4. Recommended Courses
    assert "recommended_courses" in plan
    assert isinstance(plan["recommended_courses"], list)
    assert len(plan["recommended_courses"]) > 0
    assert "trade_name" in plan["recommended_courses"][0]
    assert "target_enrolment_seats" in plan["recommended_courses"][0]

    # 5. Courses Needing Review (Obsolescence / Oversupply)
    assert "courses_needing_review" in plan
    assert isinstance(plan["courses_needing_review"], list)

    # 6. Required Training Seats Target
    assert "required_training_seats" in plan
    assert isinstance(plan["required_training_seats"], int)
    assert plan["required_training_seats"] > 0

    # 7. Required Equipment & Budget
    assert "required_equipment" in plan
    assert isinstance(plan["required_equipment"], list)
    assert "total_equipment_budget_inr" in plan
    assert plan["total_equipment_budget_inr"] > 0

    # 8. Required Trainers
    assert "required_trainers_count" in plan
    assert isinstance(plan["required_trainers_count"], int)
    assert plan["required_trainers_count"] > 0
    assert "trainer_programs" in plan

    # 9. Nearby Training Institutes
    assert "nearby_institutes" in plan
    assert isinstance(plan["nearby_institutes"], list)
    assert len(plan["nearby_institutes"]) > 0
    assert "name" in plan["nearby_institutes"][0]

    # 10. Industry Demand
    assert "industry_demand" in plan
    assert isinstance(plan["industry_demand"], list)
    assert len(plan["industry_demand"]) > 0

    # 11. Expected Impact
    assert "expected_impact" in plan
    assert isinstance(plan["expected_impact"], dict)
    assert "projected_placement_lift_pct" in plan["expected_impact"]
    assert "projected_skill_deficit_reduction_pct" in plan["expected_impact"]
    assert "total_budget_estimate_inr" in plan["expected_impact"]


def test_get_district_plan_multiple_districts():
    """Verify district plans calculate resiliently across major Maharashtra regions."""
    for district in ["Mumbai", "Nagpur", "Nashik", "Chhatrapati Sambhajinagar", "Thane"]:
        plan = get_district_plan(district)
        assert plan["district"] == district
        assert plan["required_training_seats"] > 0
        assert len(plan["top_roles"]) > 0
        assert len(plan["nearby_institutes"]) > 0
        assert plan["expected_impact"]["projected_placement_lift_pct"] > 0


def test_get_platform_metrics_summary_section33():
    """Verify get_platform_metrics_summary returns the 7 metrics specified in Section 33."""
    metrics = get_platform_metrics_summary()
    assert metrics["status"] == "success"

    # 1. Placement rate
    assert "placement_rate_pct" in metrics
    assert 0 <= metrics["placement_rate_pct"] <= 100

    # 2. Skill mismatch score
    assert "skill_mismatch_score" in metrics
    assert 0 <= metrics["skill_mismatch_score"] <= 100

    # 3. Employer approval rate
    assert "employer_approval_rate_pct" in metrics
    assert 0 <= metrics["employer_approval_rate_pct"] <= 100

    # 4. Curriculum update time (months)
    assert "avg_curriculum_update_time_months" in metrics
    assert metrics["avg_curriculum_update_time_months"] > 0

    # 5. Training capacity gaps (seats)
    assert "training_capacity_deficit_seats" in metrics
    assert metrics["training_capacity_deficit_seats"] > 0

    # 6. Equipment/trainer gaps
    assert "equipment_trainer_gap_count" in metrics
    assert metrics["equipment_trainer_gap_count"] >= 0

    # 7. Student recommendation engagement
    assert "student_engagement_rate_pct" in metrics
    assert 0 <= metrics["student_engagement_rate_pct"] <= 100


def test_districts_router_endpoints():
    """Verify FastAPI routes for districts and platform metrics."""
    # List districts
    res_list = client.get("/api/districts")
    assert res_list.status_code == 200
    data_list = res_list.json()
    assert isinstance(data_list, list)

    # District plan
    res_plan = client.get("/api/districts/Pune/plan")
    assert res_plan.status_code == 200
    data_plan = res_plan.json()
    assert data_plan["district"] == "Pune"
    assert "required_equipment" in data_plan
    assert "expected_impact" in data_plan

    # Platform metrics summary
    res_metrics = client.get("/api/districts/metrics/summary")
    assert res_metrics.status_code == 200
    data_metrics = res_metrics.json()
    assert data_metrics["status"] == "success"
    assert "placement_rate_pct" in data_metrics
    assert "skill_mismatch_score" in data_metrics
