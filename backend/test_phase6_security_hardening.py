"""Phase 6 Security and Data-Integrity Hardening Regression Tests.

Verifies:
A. Unauthenticated employer feedback mutation -> 401
B. Student attempting employer feedback mutation -> 403
C. Unrelated employer attempting to mutate another employer's feedback -> 403
D. Authorized employer feedback mutation -> succeeds (200)
E. Admin feedback mutation -> succeeds (200)
F. VALIDATED employer demand affects forecast
G. APPROVED employer demand affects forecast
H. PENDING employer demand does NOT affect forecast
I. REJECTED employer demand does NOT affect forecast
J. DEMO_SYNTHETIC employer demand does NOT affect forecast
K. PENDING employer demand does NOT affect district intelligence
L. REJECTED employer demand does NOT affect district intelligence
M. DEMO_SYNTHETIC employer demand does NOT affect district intelligence
N. VALIDATED real employer demand still affects district intelligence
"""
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.core.security import create_access_token
from app.db import (
    init_db,
    init_demo_users,
    get_demo,
    save_employer_demand,
    delete_employer_demand,
)
from app.services.forecast_engine import (
    compute_multi_horizon_forecasts,
    get_skill_forecast_trajectory,
)
from app.services.district_service import get_district_plan

init_db()
init_demo_users()
client = TestClient(app)

# Authentication tokens
EMPLOYER_1_TOKEN = create_access_token({
    "sub": "usr-employer-001",
    "email": "employer@skillsetu.gov.in",
    "role": "EMPLOYER",
})
EMPLOYER_1_HEADERS = {"Authorization": f"Bearer {EMPLOYER_1_TOKEN}"}

EMPLOYER_2_TOKEN = create_access_token({
    "sub": "usr-employer-002",
    "email": "employer2@skillsetu.gov.in",
    "role": "EMPLOYER",
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


# =========================================================================
# P0-1 Tests: Employer Feedback RBAC and Ownership Isolation
# =========================================================================

def test_a_unauthenticated_feedback_mutation_returns_401():
    """A. Unauthenticated employer feedback mutation -> 401."""
    res = client.post("/api/employer/feedback", json={
        "feedback_id": "ef-001",
        "status": "confirmed",
        "notes": "Attempt without credentials",
    })
    assert res.status_code == 401, f"Expected 401, got {res.status_code}"


def test_b_student_feedback_mutation_returns_403():
    """B. Student attempting employer feedback mutation -> 403."""
    res = client.post("/api/employer/feedback", json={
        "feedback_id": "ef-001",
        "status": "confirmed",
        "notes": "Student unauthorized attempt",
    }, headers=STUDENT_HEADERS)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}"


def test_c_unrelated_employer_feedback_mutation_returns_403():
    """C. Unrelated employer attempting to mutate another employer's feedback -> 403.
    
    ef-001 belongs to emp-001 (Tata Motors).
    usr-employer-002 belongs to emp-002 (Bajaj Auto).
    """
    res = client.post("/api/employer/feedback", json={
        "feedback_id": "ef-001",
        "status": "rejected",
        "notes": "Unrelated employer unauthorized attempt",
    }, headers=EMPLOYER_2_HEADERS)
    assert res.status_code == 403, f"Expected 403, got {res.status_code}"


def test_d_authorized_employer_feedback_mutation_succeeds():
    """D. Authorized employer feedback mutation -> succeeds (200).
    
    ef-001 belongs to emp-001.
    usr-employer-001 belongs to emp-001.
    """
    res = client.post("/api/employer/feedback", json={
        "feedback_id": "ef-001",
        "status": "confirmed",
        "notes": "Verified by Tata Motors hiring committee",
    }, headers=EMPLOYER_1_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data.get("status") == "updated"
    assert data.get("feedback", {}).get("status") == "confirmed"


def test_e_admin_feedback_mutation_succeeds():
    """E. Admin feedback mutation -> succeeds if existing Admin policy allows it."""
    res = client.post("/api/employer/feedback", json={
        "feedback_id": "ef-004",  # belongs to emp-002
        "status": "confirmed",
        "notes": "Validated by SkillSetu Administrator",
    }, headers=ADMIN_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data.get("status") == "updated"
    assert data.get("feedback", {}).get("status") == "confirmed"


# =========================================================================
# P0-2 Tests: Forecast Intelligence Validation Filtering
# =========================================================================

def test_f_validated_employer_demand_affects_forecast():
    """F. VALIDATED employer demand affects forecast."""
    # Baseline for sk-040 (Prompt Engineering)
    fc_base = get_skill_forecast_trajectory("sk-040")
    assert fc_base is not None
    base_proj = fc_base["projected_24m"]

    # Inject real VALIDATED demand
    demand_id = "ed-p6-val-001"
    save_employer_demand({
        "id": demand_id,
        "company_name": "GenAI Systems Pune",
        "job_role": "Prompt Engineer Lead",
        "validation_status": "VALIDATED",
        "status": "VALIDATED",
        "source": "EMPLOYER_SUBMITTED",
        "is_demo": False,
        "required_skills": ["Prompt Engineering"],
        "hiring_demand": "CRITICAL",
        "openings_count": 50,
    })

    try:
        fc_new = get_skill_forecast_trajectory("sk-040")
        assert fc_new["projected_24m"] > base_proj, "VALIDATED demand must increase projected 24m demand"
    finally:
        delete_employer_demand(demand_id)


def test_g_approved_employer_demand_affects_forecast():
    """G. APPROVED employer demand affects forecast."""
    fc_base = get_skill_forecast_trajectory("sk-040")
    base_proj = fc_base["projected_24m"]

    demand_id = "ed-p6-app-001"
    save_employer_demand({
        "id": demand_id,
        "company_name": "GenAI Systems Pune",
        "job_role": "Prompt Engineer Lead",
        "validation_status": "APPROVED",
        "status": "APPROVED",
        "source": "EMPLOYER_SUBMITTED",
        "is_demo": False,
        "required_skills": ["Prompt Engineering"],
        "hiring_demand": "CRITICAL",
        "openings_count": 50,
    })

    try:
        fc_new = get_skill_forecast_trajectory("sk-040")
        assert fc_new["projected_24m"] > base_proj, "APPROVED demand must increase projected 24m demand"
    finally:
        delete_employer_demand(demand_id)


def test_h_pending_employer_demand_does_not_affect_forecast():
    """H. PENDING employer demand does NOT affect forecast."""
    fc_base = get_skill_forecast_trajectory("sk-040")
    base_proj = fc_base["projected_24m"]

    demand_id = "ed-p6-pen-001"
    save_employer_demand({
        "id": demand_id,
        "company_name": "Unverified Startup",
        "job_role": "Prompt Engineer Lead",
        "validation_status": "PENDING",
        "status": "PENDING",
        "source": "EMPLOYER_SUBMITTED",
        "is_demo": False,
        "required_skills": ["Prompt Engineering"],
        "hiring_demand": "CRITICAL",
        "openings_count": 100,
    })

    try:
        fc_new = get_skill_forecast_trajectory("sk-040")
        assert fc_new["projected_24m"] == base_proj, "PENDING demand must NOT influence forecast"
    finally:
        delete_employer_demand(demand_id)


def test_i_rejected_employer_demand_does_not_affect_forecast():
    """I. REJECTED employer demand does NOT affect forecast."""
    fc_base = get_skill_forecast_trajectory("sk-040")
    base_proj = fc_base["projected_24m"]

    demand_id = "ed-p6-rej-001"
    save_employer_demand({
        "id": demand_id,
        "company_name": "Rejected Company",
        "job_role": "Prompt Engineer Lead",
        "validation_status": "REJECTED",
        "status": "REJECTED",
        "source": "EMPLOYER_SUBMITTED",
        "is_demo": False,
        "required_skills": ["Prompt Engineering"],
        "hiring_demand": "CRITICAL",
        "openings_count": 100,
    })

    try:
        fc_new = get_skill_forecast_trajectory("sk-040")
        assert fc_new["projected_24m"] == base_proj, "REJECTED demand must NOT influence forecast"
    finally:
        delete_employer_demand(demand_id)


def test_j_demo_synthetic_employer_demand_does_not_affect_forecast():
    """J. DEMO_SYNTHETIC employer demand does NOT affect forecast even if marked VALIDATED."""
    fc_base = get_skill_forecast_trajectory("sk-040")
    base_proj = fc_base["projected_24m"]

    demand_id = "ed-p6-demo-001"
    save_employer_demand({
        "id": demand_id,
        "company_name": "Synthetic Demo Co",
        "job_role": "Prompt Engineer Lead",
        "validation_status": "VALIDATED",
        "status": "VALIDATED",
        "source": "DEMO_SYNTHETIC",
        "is_demo": True,
        "required_skills": ["Prompt Engineering"],
        "hiring_demand": "CRITICAL",
        "openings_count": 100,
    })

    try:
        fc_new = get_skill_forecast_trajectory("sk-040")
        assert fc_new["projected_24m"] == base_proj, "DEMO_SYNTHETIC demand must NOT influence forecast"
    finally:
        delete_employer_demand(demand_id)


# =========================================================================
# P0-2 Tests: District Intelligence Validation Filtering
# =========================================================================

def test_k_pending_employer_demand_does_not_affect_district_intelligence():
    """K. PENDING employer demand does NOT affect district intelligence."""
    unique_role = "Quantum Cryogenic Technician PENDING"
    demand_id = "ed-p6-dist-pen-001"
    save_employer_demand({
        "id": demand_id,
        "company_name": "Cryo Labs",
        "job_role": unique_role,
        "role_title": unique_role,
        "district": "Solapur",
        "validation_status": "PENDING",
        "status": "PENDING",
        "source": "EMPLOYER_SUBMITTED",
        "is_demo": False,
        "openings_count": 500,
        "required_skills": ["Cryogenics"],
    })

    try:
        plan = get_district_plan("Solapur")
        roles = [r["role"] for r in (plan.get("top_roles") or [])]
        assert unique_role not in roles, "PENDING demand must NOT appear in district plan top roles"
    finally:
        delete_employer_demand(demand_id)


def test_l_rejected_employer_demand_does_not_affect_district_intelligence():
    """L. REJECTED employer demand does NOT affect district intelligence."""
    unique_role = "Quantum Cryogenic Technician REJECTED"
    demand_id = "ed-p6-dist-rej-001"
    save_employer_demand({
        "id": demand_id,
        "company_name": "Cryo Labs",
        "job_role": unique_role,
        "role_title": unique_role,
        "district": "Solapur",
        "validation_status": "REJECTED",
        "status": "REJECTED",
        "source": "EMPLOYER_SUBMITTED",
        "is_demo": False,
        "openings_count": 500,
        "required_skills": ["Cryogenics"],
    })

    try:
        plan = get_district_plan("Solapur")
        roles = [r["role"] for r in (plan.get("top_roles") or [])]
        assert unique_role not in roles, "REJECTED demand must NOT appear in district plan top roles"
    finally:
        delete_employer_demand(demand_id)


def test_m_demo_synthetic_employer_demand_does_not_affect_district_intelligence():
    """M. DEMO_SYNTHETIC employer demand does NOT affect district intelligence even if marked VALIDATED."""
    unique_role = "Quantum Cryogenic Technician DEMO"
    demand_id = "ed-p6-dist-demo-001"
    save_employer_demand({
        "id": demand_id,
        "company_name": "Demo Synthetic Corp",
        "job_role": unique_role,
        "role_title": unique_role,
        "district": "Solapur",
        "validation_status": "VALIDATED",
        "status": "VALIDATED",
        "source": "DEMO_SYNTHETIC",
        "is_demo": True,
        "openings_count": 500,
        "required_skills": ["Cryogenics"],
    })

    try:
        plan = get_district_plan("Solapur")
        roles = [r["role"] for r in (plan.get("top_roles") or [])]
        assert unique_role not in roles, "DEMO_SYNTHETIC demand must NOT appear in district plan top roles"
    finally:
        delete_employer_demand(demand_id)


def test_n_validated_real_employer_demand_affects_district_intelligence():
    """N. VALIDATED real employer demand still affects district intelligence."""
    unique_role = "Precision Solar Roboticist VALIDATED"
    demand_id = "ed-p6-dist-val-001"
    save_employer_demand({
        "id": demand_id,
        "company_name": "Maharashtra Green Energy Ltd",
        "job_role": unique_role,
        "role_title": unique_role,
        "district": "Solapur",
        "validation_status": "VALIDATED",
        "status": "VALIDATED",
        "source": "EMPLOYER_SUBMITTED",
        "is_demo": False,
        "openings_count": 500,
        "required_skills": ["Solar PV Systems"],
    })

    try:
        plan = get_district_plan("Solapur")
        roles = [r["role"] for r in (plan.get("top_roles") or [])]
        assert unique_role in roles, "VALIDATED real demand MUST appear in district plan top roles"
    finally:
        delete_employer_demand(demand_id)
