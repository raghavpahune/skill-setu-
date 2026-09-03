"""Phase 32F Test Suite: Supabase System-of-Record Foundation for skill_forecasts.

Verifies:
1. Repository get
2. Repository list
3. Repository create
4. Repository update
5. Repository delete
6. API reads bypass stale cache
7. Supabase persistence
8. Supabase read failure -> 5xx
9. Supabase write failure -> 5xx
10. Authentication / RBAC enforcement
11. Admin governance behavior
12. Demo / synthetic exclusion
13. Validated / approved input behavior
14. Forecast computation and persistence (zero duplicate rows)
15. Downstream consumers read Supabase
16. Scheduler forecast persistence path
17. Phase 32A regression (employer feedback)
18. Phase 32B regression (employer demands)
19. Phase 32C regression (student profiles & assessments)
20. Phase 32D regression (courses)
21. Phase 32E regression (industry signals)
"""
import uuid
import pytest
from unittest.mock import patch
from starlette.testclient import TestClient

from app.main import app
from app.core.security import create_access_token
from app.repositories.supabase_repository import (
    get_skill_forecast,
    list_skill_forecasts,
    create_skill_forecast,
    update_skill_forecast_repo,
    delete_skill_forecast_repo,
    SkillForecastNotFoundError,
    SupabaseRepositoryError,
    get_employer_feedback,
    get_employer_demand,
    get_student_profile,
    get_course,
    get_industry_signal,
)
from app.db import _cache, init_db, init_demo_users
from app.services.forecast_engine import (
    compute_multi_horizon_forecasts,
    get_skill_forecast_trajectory,
    persist_computed_forecasts,
)

init_db()
init_demo_users()

client = TestClient(app)

ADMIN_TOKEN = create_access_token({
    "sub": "usr-admin-001",
    "email": "admin@skillsetu.gov.in",
    "role": "ADMIN",
})
ADMIN_HEADERS = {"Authorization": f"Bearer {ADMIN_TOKEN}"}

STUDENT_TOKEN = create_access_token({
    "sub": "usr-student-001",
    "email": "student@skillsetu.gov.in",
    "role": "STUDENT",
})
STUDENT_HEADERS = {"Authorization": f"Bearer {STUDENT_TOKEN}"}


# =========================================================================
# 1. Repository Get
# =========================================================================

def test_01_repository_get():
    """Verify get_skill_forecast returns correct record or None."""
    sf_id = f"sf-test-{uuid.uuid4().hex[:8]}"
    create_skill_forecast({
        "id": sf_id,
        "skill_id": "sk-001",
        "period": "12m",
        "current_demand": "high",
        "future_demand": "very_high",
        "trend": "rising",
        "confidence": 92,
    })

    record = get_skill_forecast(sf_id)
    assert record is not None
    assert record["id"] == sf_id
    assert record["skill_id"] == "sk-001"
    assert record["period"] == "12m"
    assert record["confidence"] == 92

    non_existent = get_skill_forecast("sf-non-existent-999")
    assert non_existent is None
    delete_skill_forecast_repo(sf_id)


# =========================================================================
# 2. Repository List
# =========================================================================

def test_02_repository_list():
    """Verify list_skill_forecasts returns records with optional filters."""
    sf_id = f"sf-list-{uuid.uuid4().hex[:8]}"
    create_skill_forecast({
        "id": sf_id,
        "skill_id": "sk-040",
        "period": "24m",
        "current_demand": "medium",
        "future_demand": "high",
        "trend": "rising",
        "confidence": 85,
    })

    all_fc = list_skill_forecasts()
    assert len(all_fc) > 0
    assert any(f["id"] == sf_id for f in all_fc)

    # Filter by skill_id
    by_skill = list_skill_forecasts(skill_id="sk-040")
    assert all(f["skill_id"] == "sk-040" for f in by_skill)

    # Filter by period
    by_period = list_skill_forecasts(period="24m")
    assert all(f["period"] == "24m" for f in by_period)

    delete_skill_forecast_repo(sf_id)


# =========================================================================
# 3. Repository Create
# =========================================================================

def test_03_repository_create():
    """Verify create_skill_forecast persists and assigns ID if missing."""
    data = {
        "skill_id": "sk-002",
        "period": "6m",
        "current_demand": "low",
        "future_demand": "medium",
        "trend": "stable",
        "confidence": 75,
    }
    saved = create_skill_forecast(data)
    assert saved["id"] is not None
    assert saved["skill_id"] == "sk-002"
    assert saved["trend"] == "stable"

    fetched = get_skill_forecast(saved["id"])
    assert fetched is not None
    assert fetched["confidence"] == 75
    delete_skill_forecast_repo(saved["id"])


# =========================================================================
# 4. Repository Update
# =========================================================================

def test_04_repository_update():
    """Verify update_skill_forecast_repo modifies fields and raises on missing."""
    sf_id = f"sf-upd-{uuid.uuid4().hex[:8]}"
    create_skill_forecast({
        "id": sf_id,
        "skill_id": "sk-003",
        "period": "12m",
        "current_demand": "medium",
        "future_demand": "high",
        "trend": "rising",
        "confidence": 80,
    })

    updated = update_skill_forecast_repo(sf_id, {"future_demand": "very_high", "confidence": 95})
    assert updated["future_demand"] == "very_high"
    assert updated["confidence"] == 95

    re_fetched = get_skill_forecast(sf_id)
    assert re_fetched["confidence"] == 95

    with pytest.raises(SkillForecastNotFoundError):
        update_skill_forecast_repo("sf-ghost-row", {"confidence": 50})

    delete_skill_forecast_repo(sf_id)


# =========================================================================
# 5. Repository Delete
# =========================================================================

def test_05_repository_delete():
    """Verify delete_skill_forecast_repo deletes record."""
    sf_id = f"sf-del-{uuid.uuid4().hex[:8]}"
    create_skill_forecast({
        "id": sf_id,
        "skill_id": "sk-004",
        "period": "6m",
        "current_demand": "high",
        "future_demand": "high",
        "trend": "stable",
        "confidence": 88,
    })

    deleted = delete_skill_forecast_repo(sf_id)
    assert deleted is True
    assert get_skill_forecast(sf_id) is None


# =========================================================================
# 6. API reads bypass stale cache
# =========================================================================

def test_06_api_reads_bypass_stale_cache():
    """Public forecast endpoint reads from Supabase, not local _cache."""
    sf_id = f"sf-cache-bypass-{uuid.uuid4().hex[:8]}"
    create_skill_forecast({
        "id": sf_id,
        "skill_id": "sk-055",
        "period": "12m",
        "current_demand": "high",
        "future_demand": "very_high",
        "trend": "rising",
        "confidence": 94,
    })

    # Empty local cache table for skill_forecasts
    _cache["skill_forecasts"] = []

    resp = client.get("/api/forecast")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) > 0

    # Skill specific endpoint
    resp_skill = client.get("/api/forecast/skill/sk-055")
    assert resp_skill.status_code == 200
    assert len(resp_skill.json()) > 0
    assert resp_skill.json()[0]["skill_id"] == "sk-055"

    delete_skill_forecast_repo(sf_id)


# =========================================================================
# 7. Supabase persistence
# =========================================================================

def test_07_supabase_persistence():
    """Admin API writes persist authoritatively in Supabase repository."""
    resp = client.post(
        "/api/admin/forecasts",
        json={
            "skill_id": "sk-019",
            "period": "6m",
            "current_demand": "low",
            "future_demand": "high",
            "trend": "rising",
            "confidence": 82,
        },
        headers=ADMIN_HEADERS,
    )
    assert resp.status_code == 200
    saved = resp.json()["forecast"]
    sf_id = saved["id"]

    # Verify directly via repository
    repo_item = get_skill_forecast(sf_id)
    assert repo_item is not None
    assert repo_item["skill_id"] == "sk-019"

    # Patch via admin API
    patch_resp = client.patch(
        f"/api/admin/forecasts/{sf_id}",
        json={"future_demand": "very_high", "confidence": 90},
        headers=ADMIN_HEADERS,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["forecast"]["confidence"] == 90

    # Delete via admin API
    del_resp = client.delete(f"/api/admin/forecasts/{sf_id}", headers=ADMIN_HEADERS)
    assert del_resp.status_code == 200
    assert get_skill_forecast(sf_id) is None


# =========================================================================
# 8. Supabase read failure -> 5xx
# =========================================================================

def test_08_supabase_read_failure_returns_500():
    """When Supabase list fails, public and admin endpoints return HTTP 500."""
    with patch("app.repositories.supabase_repository.list_skill_forecasts", side_effect=SupabaseRepositoryError("DB read timeout")):
        resp = client.get("/api/forecast")
        assert resp.status_code == 500
        assert "Database query failed" in resp.json()["detail"]

        resp_admin = client.get("/api/admin/forecasts", headers=ADMIN_HEADERS)
        assert resp_admin.status_code == 500


# =========================================================================
# 9. Supabase write failure -> 5xx
# =========================================================================

def test_09_supabase_write_failure_returns_500():
    """When Supabase write fails, admin mutation endpoints return HTTP 500."""
    with patch("app.repositories.supabase_repository.create_skill_forecast", side_effect=SupabaseRepositoryError("DB write connection failed")):
        resp = client.post(
            "/api/admin/forecasts",
            json={"skill_id": "sk-001", "period": "6m", "trend": "rising", "confidence": 80},
            headers=ADMIN_HEADERS,
        )
        assert resp.status_code == 500

    with patch("app.repositories.supabase_repository.update_skill_forecast_repo", side_effect=SupabaseRepositoryError("DB update failed")):
        resp = client.patch(
            "/api/admin/forecasts/sf-any",
            json={"confidence": 90},
            headers=ADMIN_HEADERS,
        )
        assert resp.status_code == 500

    with patch("app.repositories.supabase_repository.delete_skill_forecast_repo", side_effect=SupabaseRepositoryError("DB delete failed")):
        resp = client.delete("/api/admin/forecasts/sf-any", headers=ADMIN_HEADERS)
        assert resp.status_code == 500


# =========================================================================
# 10. Authentication / RBAC enforcement
# =========================================================================

def test_10_authentication_rbac():
    """Unauthenticated or unauthorized roles are blocked from admin forecast endpoints."""
    # Unauthenticated
    assert client.get("/api/admin/forecasts").status_code in (401, 403)
    assert client.post("/api/admin/forecasts", json={"skill_id": "sk-001", "period": "6m"}).status_code in (401, 403)
    assert client.patch("/api/admin/forecasts/sf-1", json={"confidence": 80}).status_code in (401, 403)
    assert client.delete("/api/admin/forecasts/sf-1").status_code in (401, 403)

    # Student forbidden
    assert client.get("/api/admin/forecasts", headers=STUDENT_HEADERS).status_code in (401, 403)
    assert client.post("/api/admin/forecasts", json={"skill_id": "sk-001", "period": "6m"}, headers=STUDENT_HEADERS).status_code in (401, 403)
    assert client.delete("/api/admin/forecasts/sf-1", headers=STUDENT_HEADERS).status_code in (401, 403)


# =========================================================================
# 11. Admin governance behavior
# =========================================================================

def test_11_admin_governance_behavior():
    """Admin can list and recompute forecasts with full governance capability."""
    resp = client.get("/api/admin/forecasts?limit=5", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "forecasts" in data

    # Recompute and persist endpoint
    recompute_resp = client.post("/api/admin/forecasts/recompute", headers=ADMIN_HEADERS)
    assert recompute_resp.status_code == 200
    assert recompute_resp.json()["status"] == "success"
    assert recompute_resp.json()["count"] > 0


# =========================================================================
# 12. Demo / synthetic exclusion
# =========================================================================

def test_12_demo_synthetic_exclusion():
    """DEMO_SYNTHETIC employer demands must NOT affect forecast calculations."""
    fc_base = get_skill_forecast_trajectory("sk-040")
    base_proj = fc_base["projected_24m"]

    from app.repositories.supabase_repository import create_employer_demand, delete_employer_demand_repo
    dem_id = f"dem-demo-exclude-{uuid.uuid4().hex[:8]}"
    create_employer_demand({
        "id": dem_id,
        "organization_id": "emp-synth-test",
        "company_name": "Synthetic Corp",
        "job_role": "AI Specialist",
        "required_skills": ["sk-040"],
        "hiring_demand": "CRITICAL",
        "status": "VALIDATED",
        "validation_status": "VALIDATED",
        "source": "DEMO_SYNTHETIC",
        "source_label": "DEMO_SYNTHETIC",
        "is_demo": True,
        "is_active": True,
    })

    try:
        fc_after = get_skill_forecast_trajectory("sk-040")
        assert fc_after["projected_24m"] == base_proj, "Synthetic demand must not inflate forecast"
    finally:
        delete_employer_demand_repo(dem_id)


# =========================================================================
# 13. Validated / approved input behavior
# =========================================================================

def test_13_validated_approved_input_behavior():
    """Real VALIDATED / APPROVED employer demands influence forecasts; PENDING / REJECTED do not."""
    fc_base = get_skill_forecast_trajectory("sk-040")
    base_proj = fc_base["projected_24m"]

    from app.repositories.supabase_repository import create_employer_demand, delete_employer_demand_repo

    # 1. PENDING demand -> NO influence
    pend_id = f"dem-pend-{uuid.uuid4().hex[:8]}"
    create_employer_demand({
        "id": pend_id,
        "organization_id": "emp-real-001",
        "company_name": "Real Tech Corp",
        "job_role": "AI Specialist",
        "required_skills": ["sk-040"],
        "hiring_demand": "CRITICAL",
        "status": "PENDING",
        "validation_status": "PENDING",
        "source": "EMPLOYER_SUBMITTED",
        "is_demo": False,
        "is_active": True,
    })
    try:
        fc_pend = get_skill_forecast_trajectory("sk-040")
        assert fc_pend["projected_24m"] == base_proj
    finally:
        delete_employer_demand_repo(pend_id)

    # 2. VALIDATED demand -> Positive influence
    val_id = f"dem-val-{uuid.uuid4().hex[:8]}"
    create_employer_demand({
        "id": val_id,
        "organization_id": "emp-real-002",
        "company_name": "Real Tech Corp 2",
        "job_role": "AI Specialist",
        "required_skills": ["Prompt Engineering"],
        "hiring_demand": "CRITICAL",
        "status": "VALIDATED",
        "validation_status": "VALIDATED",
        "source": "EMPLOYER_SUBMITTED",
        "is_demo": False,
        "is_active": True,
    })
    try:
        fc_val = get_skill_forecast_trajectory("sk-040")
        assert fc_val["projected_24m"] > base_proj
    finally:
        delete_employer_demand_repo(val_id)


# =========================================================================
# 14. Forecast computation and persistence
# =========================================================================

def test_14_forecast_computation_and_persistence():
    """persist_computed_forecasts writes multi-horizon rows without duplicates."""
    initial_count = len(list_skill_forecasts())
    persisted = persist_computed_forecasts()
    assert len(persisted) > 0

    # Check check constraint validity on persisted items
    for item in persisted[:10]:
        assert item["period"] in ("6m", "12m", "24m")
        assert item["current_demand"] in ("low", "medium", "high", "very_high")
        assert item["future_demand"] in ("low", "medium", "high", "very_high")
        assert item["trend"] in ("rising", "stable", "declining")
        assert 0 <= item["confidence"] <= 100

    # Re-running must not create duplicate (skill_id, period) rows
    after_count = len(list_skill_forecasts())
    persist_computed_forecasts()
    second_after_count = len(list_skill_forecasts())
    assert second_after_count == after_count, "Repeated forecast persistence must not create duplicate rows"


# =========================================================================
# 15. Downstream consumers read Supabase
# =========================================================================

def test_15_downstream_consumers_read_supabase():
    """Verify student roadmap, simulator, recommendation and student services read Supabase."""
    from app.services.recommendation_service import get_curriculum_recommendations
    from app.services.student_service import get_skill_explainability

    # 1. Curriculum recommendations
    recs = get_curriculum_recommendations()
    assert isinstance(recs, list)

    # 2. Skill explainability
    expl = get_skill_explainability("Python")
    assert "dimension_2_future_forecast" in expl.get("explainability", {})
    assert expl["explainability"]["dimension_2_future_forecast"]["verified"] is True

    # 3. Simulator curriculum stale
    from app.routers.simulator import _simulate_curriculum_stale, WhatIfScenario
    baseline = {"avg_skill_gap_pct": 50.0, "placement_rate_pct": 70.0}
    scenario = WhatIfScenario(scenario_type="curriculum_stale", stale_years=2)
    sim_res = _simulate_curriculum_stale(baseline, scenario)
    assert "projected_avg_gap_pct" in sim_res

    # 4. Student roadmap endpoint
    roadmap_resp = client.get("/api/student/me/roadmap", headers=STUDENT_HEADERS)
    assert roadmap_resp.status_code in (200, 404)


# =========================================================================
# 16. Scheduler forecast persistence path
# =========================================================================

@pytest.mark.anyio
async def test_16_scheduler_forecast_persistence_path():
    """Verify IngestionScheduler execute_sync with source='skill_forecasts' persists to Supabase."""
    from app.ingestion.scheduler import IngestionScheduler
    sched = IngestionScheduler()
    res = await sched.execute_sync(source="skill_forecasts")
    assert res["status"] == "success"
    assert res["source"] == "skill_forecasts"
    assert res["forecasts_persisted"] > 0


# =========================================================================
# 17. Phase 32A Regression: Employer Feedback
# =========================================================================

def test_17_phase32a_regression_feedback():
    """Verify Phase 32A employer feedback repository remains intact."""
    fb = get_employer_feedback("ef-001")
    assert fb is not None
    assert fb.get("status") in ("pending", "confirmed", "corrected")


# =========================================================================
# 18. Phase 32B Regression: Employer Demands
# =========================================================================

def test_18_phase32b_regression_demands():
    """Verify Phase 32B employer demands repository remains intact."""
    demands = client.get("/api/employer/demands")
    assert demands.status_code == 200


# =========================================================================
# 19. Phase 32C Regression: Student Profiles & Assessments
# =========================================================================

def test_19_phase32c_regression_students():
    """Verify Phase 32C student profiles repository remains intact."""
    p = get_student_profile("stu-001")
    assert p is not None


# =========================================================================
# 20. Phase 32D Regression: Courses
# =========================================================================

def test_20_phase32d_regression_courses():
    """Verify Phase 32D courses repository remains intact."""
    c = get_course("cr-001")
    assert c is not None
    assert "name" in c or "title" in c


# =========================================================================
# 21. Phase 32E Regression: Industry Signals
# =========================================================================

def test_21_phase32e_regression_industry_signals():
    """Verify Phase 32E industry signals repository remains intact."""
    signals_resp = client.get("/api/industry/signals")
    assert signals_resp.status_code == 200
    assert "signals" in signals_resp.json()
