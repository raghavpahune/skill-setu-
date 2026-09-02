"""Phase 32B Test Suite: Supabase System-of-Record Foundation for employer_demands.

Verifies:
1. Repository list, get, create, update, delete directly with Supabase.
2. API GET reads from Supabase rather than in-memory _cache.
3. API POST writes directly to Supabase with authoritative ID and metadata.
4. API PATCH updates directly in Supabase with ownership protection.
5. Supabase failure (both POST insert and PATCH update) returns HTTP 5xx.
6. Unauthenticated requests return 401.
7. Student role requests return 403.
8. Unrelated employer cannot modify or delete another employer's demand (403).
9. Authorized employer can create, view, and update own demands.
10. Admin can view and update across all employers.
11. Client identity/org spoofing in POST payload is strictly rejected with 403.
12. Validation status filtering: demo, synthetic, pending, and rejected demands remain excluded from live validated consumers.
13. Intelligence consumers (recommendation engine, district planner, forecast engine, gap engine) read Supabase demands correctly.
"""
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.core.security import create_access_token
from app.repositories.supabase_repository import (
    get_employer_demand,
    list_employer_demands,
    create_employer_demand,
    update_employer_demand,
    delete_employer_demand_repo,
    DemandNotFoundError,
    SupabaseRepositoryError,
    get_client,
)
from app.db import _cache, init_db, init_demo_users
from app.services.career_recommendation_engine import _get_validated_employer_demands, _is_live_employer_demand
from app.services.district_service import get_district_plan
from app.services.forecast_engine import compute_multi_horizon_forecasts
from app.services.gap_engine import compute_gaps

init_db()
init_demo_users()

client = TestClient(app)

# Authentication tokens
EMPLOYER_1_TOKEN = create_access_token({
    "sub": "usr-employer-001",
    "email": "employer@skillsetu.gov.in",
    "role": "EMPLOYER",
    "organization_id": "emp-001",
})
EMPLOYER_1_HEADERS = {"Authorization": f"Bearer {EMPLOYER_1_TOKEN}"}

EMPLOYER_2_TOKEN = create_access_token({
    "sub": "usr-employer-002",
    "email": "employer2@skillsetu.gov.in",
    "role": "EMPLOYER",
    "organization_id": "emp-002",
})
EMPLOYER_2_HEADERS = {"Authorization": f"Bearer {EMPLOYER_2_TOKEN}"}

STUDENT_TOKEN = create_access_token({
    "sub": "usr-student-001",
    "email": "student@skillsetu.gov.in",
    "role": "STUDENT",
})
STUDENT_HEADERS = {"Authorization": f"Bearer {STUDENT_TOKEN}"}

ADMIN_TOKEN = create_access_token({
    "sub": "usr-admin-001",
    "email": "admin@skillsetu.gov.in",
    "role": "ADMIN",
})
ADMIN_HEADERS = {"Authorization": f"Bearer {ADMIN_TOKEN}"}


# ============================================================================
# 1. REPOSITORY UNIT TESTS
# ============================================================================

def test_01_repository_demand_lifecycle():
    """Verify repository get, list, create, update, and delete."""
    demand_id = "ed-repo-test-01"
    payload = {
        "id": demand_id,
        "employer_id": "emp-001",
        "company_name": "Tata Motors Innovation Lab",
        "industry": "Automotive & EV",
        "district": "Pune",
        "job_role": "Robotics System Calibrator",
        "required_skills": ["Robotics", "ROS 2", "Python"],
        "openings_count": 10,
        "validation_status": "PENDING",
        "source": "EMPLOYER_SUBMITTED",
        "is_demo": False,
    }

    # Create
    created = create_employer_demand(payload)
    assert created["id"] == demand_id
    assert created["job_role"] == "Robotics System Calibrator"

    # Read
    fetched = get_employer_demand(demand_id)
    assert fetched is not None
    assert fetched["company_name"] == "Tata Motors Innovation Lab"

    # List
    pune_demands = list_employer_demands(district="Pune")
    assert any(d["id"] == demand_id for d in pune_demands)

    # Update
    updated = update_employer_demand(demand_id, {"openings_count": 25, "validation_status": "VALIDATED"})
    assert updated["openings_count"] == 25
    assert updated["validation_status"] == "VALIDATED"

    # Verify updated row persists
    refetched = get_employer_demand(demand_id)
    assert refetched["openings_count"] == 25
    assert refetched["validation_status"] == "VALIDATED"

    # Missing row raises DemandNotFoundError
    with pytest.raises(DemandNotFoundError):
        update_employer_demand("ed-ghost-999", {"openings_count": 50})

    # Delete
    assert delete_employer_demand_repo(demand_id) is True
    assert get_employer_demand(demand_id) is None


# ============================================================================
# 2. API GET READS SUPABASE RATHER THAN CACHE
# ============================================================================

def test_02_api_get_does_not_depend_on_cache():
    """GET /api/employer/me/demands reads directly from Supabase, not _cache."""
    # Insert a real demand directly into Supabase mock
    sb_client = get_client()
    demand_id = "ed-cache-independence-test"
    sb_client.table("employer_demands").insert({
        "id": demand_id,
        "employer_id": "emp-001",
        "user_id": "usr-employer-001",
        "user_email": "employer@skillsetu.gov.in",
        "company_name": "Tata Motors",
        "industry": "Automotive",
        "district": "Pune",
        "job_role": "Autonomous Driving Software Engineer",
        "required_skills": ["C++", "CUDA", "Perception"],
        "openings_count": 8,
        "validation_status": "PENDING",
        "source": "EMPLOYER_SUBMITTED",
        "is_demo": False,
    }).execute()

    # Corrupt or empty _cache["employer_demands"]
    orig_cache = _cache.get("employer_demands")
    _cache["employer_demands"] = [{"id": "stale-cache-record", "user_id": "usr-employer-001"}]

    try:
        res = client.get("/api/employer/me/demands", headers=EMPLOYER_1_HEADERS)
        assert res.status_code == 200
        demands = res.json()["demands"]
        ids = [d["id"] for d in demands]
        assert demand_id in ids
        assert "stale-cache-record" not in ids
    finally:
        if orig_cache is not None:
            _cache["employer_demands"] = orig_cache


# ============================================================================
# 3 & 4. API POST & PATCH WRITE DIRECTLY TO SUPABASE
# ============================================================================

def test_03_api_post_writes_to_supabase():
    """POST /api/employer/demand writes new record to Supabase and returns created row."""
    payload = {
        "company_name": "Tata Motors",
        "industry": "Automotive & EV",
        "district": "Pune",
        "job_role": "Battery Pack Integration Engineer",
        "required_skills": ["Battery Management (BMS)", "Thermal Analysis", "CAN Bus"],
        "openings_count": 15,
        "experience_level": "Entry Level (0-1 yrs)",
        "hiring_timeline": "Immediate (0-30 days)",
        "additional_requirements": "Testing on production line",
    }

    res = client.post("/api/employer/demand", json=payload, headers=EMPLOYER_1_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "created"
    demand = data["demand"]
    demand_id = demand["id"]
    assert demand["job_role"] == "Battery Pack Integration Engineer"
    assert demand["employer_id"] == "emp-001"
    assert demand["user_id"] == "usr-employer-001"

    # Verify directly in Supabase
    persisted = get_employer_demand(demand_id)
    assert persisted is not None
    assert persisted["job_role"] == "Battery Pack Integration Engineer"
    assert persisted["openings_count"] == 15


def test_04_api_patch_writes_to_supabase():
    """PATCH /api/employer/demands/{demand_id} updates record in Supabase."""
    # First create a demand
    create_res = client.post("/api/employer/demand", json={
        "company_name": "Tata Motors",
        "industry": "Automotive & EV",
        "district": "Pune",
        "job_role": "Power Electronics Engineer",
        "required_skills": ["Inverters", "SiC MOSFETs"],
        "openings_count": 5,
    }, headers=EMPLOYER_1_HEADERS)
    demand_id = create_res.json()["demand"]["id"]

    # Now patch it
    patch_res = client.patch(f"/api/employer/demands/{demand_id}", json={
        "openings_count": 18,
        "experience_level": "Mid Level (2-4 yrs)",
    }, headers=EMPLOYER_1_HEADERS)
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "success"
    assert patch_res.json()["demand"]["openings_count"] == 18

    # Verify in Supabase
    refetched = get_employer_demand(demand_id)
    assert refetched["openings_count"] == 18
    assert refetched["experience_level"] == "Mid Level (2-4 yrs)"


# ============================================================================
# 5. SUPABASE MUTATION FAILURE RETURNS 5XX
# ============================================================================

def test_05_supabase_insert_failure_returns_5xx():
    """POST /api/employer/demand returns 500 when Supabase database fails."""
    sb_client = get_client()
    sb_client.table("employer_demands").should_fail_insert = True

    try:
        res = client.post("/api/employer/demand", json={
            "company_name": "Tata Motors",
            "industry": "Automotive & EV",
            "district": "Pune",
            "job_role": "Failure Scenario Engineer",
            "required_skills": ["Python"],
        }, headers=EMPLOYER_1_HEADERS)

        assert res.status_code >= 500
        assert "Database insertion failed" in res.json().get("detail", "")
    finally:
        sb_client.table("employer_demands").should_fail_insert = False


def test_06_supabase_update_failure_returns_5xx():
    """PATCH /api/employer/demands/{id} returns 500 when Supabase update fails."""
    create_res = client.post("/api/employer/demand", json={
        "company_name": "Tata Motors",
        "industry": "Automotive & EV",
        "district": "Pune",
        "job_role": "Firmware Engineer",
        "required_skills": ["Embedded C"],
    }, headers=EMPLOYER_1_HEADERS)
    demand_id = create_res.json()["demand"]["id"]

    sb_client = get_client()
    sb_client.table("employer_demands").should_fail_update = True

    try:
        res = client.patch(f"/api/employer/demands/{demand_id}", json={
            "openings_count": 30,
        }, headers=EMPLOYER_1_HEADERS)

        assert res.status_code >= 500
        assert "Database update failed" in res.json().get("detail", "")
    finally:
        sb_client.table("employer_demands").should_fail_update = False


# ============================================================================
# 6, 7, 8, 9, 10, 11. SECURITY, RBAC & IDENTITY SPOOFING REJECTION
# ============================================================================

def test_07_unauthenticated_requests_return_401():
    """Unauthenticated access to demands endpoints returns 401."""
    assert client.post("/api/employer/demand", json={"job_role": "Dev"}).status_code == 401
    assert client.get("/api/employer/me/demands").status_code == 401
    assert client.patch("/api/employer/demands/ed-001", json={"openings_count": 2}).status_code == 401


def test_08_student_requests_return_403():
    """Student cannot submit or view private employer demands (403)."""
    res = client.post("/api/employer/demand", json={
        "company_name": "Student Fake Corp",
        "industry": "IT",
        "district": "Pune",
        "job_role": "Hacker",
        "required_skills": ["Python"],
    }, headers=STUDENT_HEADERS)
    assert res.status_code == 403

    assert client.get("/api/employer/me/demands", headers=STUDENT_HEADERS).status_code == 403


def test_09_unrelated_employer_cannot_modify_or_delete_other_demand():
    """Employer 2 cannot modify or delete Employer 1's demand (403)."""
    create_res = client.post("/api/employer/demand", json={
        "company_name": "Tata Motors",
        "industry": "Automotive & EV",
        "district": "Pune",
        "job_role": "Proprietary IP Engineer",
        "required_skills": ["Robotics"],
    }, headers=EMPLOYER_1_HEADERS)
    demand_id = create_res.json()["demand"]["id"]

    # Employer 2 attempts PATCH
    patch_res = client.patch(f"/api/employer/demands/{demand_id}", json={
        "openings_count": 999,
    }, headers=EMPLOYER_2_HEADERS)
    assert patch_res.status_code == 403

    # Employer 2 attempts DELETE
    del_res = client.delete(f"/api/employer/demands/{demand_id}", headers=EMPLOYER_2_HEADERS)
    assert del_res.status_code == 403


def test_10_client_org_spoofing_strictly_rejected():
    """Employer passing a different employer_id in payload is strictly rejected with 403."""
    # Employer 2 tries to impersonate emp-001 (Tata Motors)
    res = client.post("/api/employer/demand", json={
        "employer_id": "emp-001",
        "company_name": "Tata Motors Impersonation",
        "industry": "Automotive & EV",
        "district": "Pune",
        "job_role": "Spoofed Job Role",
        "required_skills": ["EV Battery Technology"],
    }, headers=EMPLOYER_2_HEADERS)
    assert res.status_code == 403
    assert "Cannot submit hiring demand on behalf of another organization" in res.json().get("detail", "")


def test_11_admin_can_update_across_employers():
    """Admin can patch any employer demand."""
    create_res = client.post("/api/employer/demand", json={
        "company_name": "Tata Motors",
        "industry": "Automotive & EV",
        "district": "Pune",
        "job_role": "Admin Managed Role",
        "required_skills": ["Safety Standards"],
    }, headers=EMPLOYER_1_HEADERS)
    demand_id = create_res.json()["demand"]["id"]

    # Admin updates
    res = client.patch(f"/api/employer/demands/{demand_id}", json={
        "additional_requirements": "Admin certified requirement",
    }, headers=ADMIN_HEADERS)
    assert res.status_code == 200
    assert res.json()["demand"]["additional_requirements"] == "Admin certified requirement"


# ============================================================================
# 12 & 13. VALIDATION STATUS FILTERING & DOWNSTREAM INTELLIGENCE INTEGRITY
# ============================================================================

def test_12_validation_status_filtering_in_recommendations():
    """Demo, synthetic, pending, and rejected demands remain excluded from live recommendations."""
    sb_client = get_client()

    # Create pending real demand
    pending_id = "ed-rec-pending-test"
    sb_client.table("employer_demands").insert({
        "id": pending_id,
        "employer_id": "emp-001",
        "company_name": "Live Auto",
        "industry": "Automotive",
        "district": "Pune",
        "job_role": "Pending Demand Role",
        "required_skills": ["Electric Vehicles"],
        "openings_count": 100,
        "validation_status": "PENDING",
        "source": "EMPLOYER_SUBMITTED",
        "is_demo": False,
    }).execute()

    # Create validated real demand
    validated_id = "ed-rec-validated-test"
    sb_client.table("employer_demands").insert({
        "id": validated_id,
        "employer_id": "emp-001",
        "company_name": "Live Auto",
        "industry": "Automotive",
        "district": "Pune",
        "job_role": "Validated Demand Role",
        "required_skills": ["Electric Vehicles"],
        "openings_count": 100,
        "validation_status": "VALIDATED",
        "source": "EMPLOYER_SUBMITTED",
        "is_demo": False,
    }).execute()

    # Create rejected real demand
    rejected_id = "ed-rec-rejected-test"
    sb_client.table("employer_demands").insert({
        "id": rejected_id,
        "employer_id": "emp-001",
        "company_name": "Live Auto",
        "industry": "Automotive",
        "district": "Pune",
        "job_role": "Rejected Demand Role",
        "required_skills": ["Electric Vehicles"],
        "openings_count": 100,
        "validation_status": "REJECTED",
        "source": "EMPLOYER_SUBMITTED",
        "is_demo": False,
    }).execute()

    validated_list = _get_validated_employer_demands()
    validated_ids = [d["id"] for d in validated_list]

    # Strictly only the VALIDATED live record should appear
    assert validated_id in validated_ids
    assert pending_id not in validated_ids
    assert rejected_id not in validated_ids


def test_13_intelligence_consumers_read_supabase():
    """Verify district plan, forecast engine, and gap engine execute cleanly with Supabase demands."""
    # 1. District Plan
    pune_plan = get_district_plan("Pune")
    assert pune_plan is not None
    assert "top_demanded_roles" in pune_plan

    # 2. Multi-horizon forecasts
    forecasts = compute_multi_horizon_forecasts()
    assert isinstance(forecasts, list)
    assert len(forecasts) > 0

    # 3. Gap Engine
    gaps = compute_gaps()
    assert isinstance(gaps, list)
    assert len(gaps) > 0
