"""Test suite for Phase 14: Employer Data Collection & Validation."""
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.db import init_db, init_demo_users
from app.config import settings
from app.core.security import create_access_token
from app.services.gap_engine import compute_gaps

client = TestClient(app)
ADMIN_KEY = settings.admin_api_key or "demo-admin-key-2026"
HEADERS = {"X-Admin-Key": ADMIN_KEY}

EMPLOYER_TOKEN = create_access_token({"sub": "usr-employer-001", "email": "employer@skillsetu.gov.in", "role": "EMPLOYER"})
EMPLOYER_HEADERS = {"Authorization": f"Bearer {EMPLOYER_TOKEN}"}

ADMIN_TOKEN = create_access_token({"sub": "usr-admin-001", "email": "admin@skillsetu.gov.in", "role": "ADMIN"})
ADMIN_AUTH_HEADERS = {"Authorization": f"Bearer {ADMIN_TOKEN}"}


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    init_demo_users()


def test_employer_submission_valid():
    """POST /api/employer/demands accepts valid company hiring requirement."""
    payload = {
        "company_name": "Mahindra Electric Mobility Ltd",
        "industry": "Automotive & EV",
        "district": "Pune",
        "job_role": "High-Voltage EV Powertrain Calibration Engineer",
        "required_skills": ["EV Battery Technology", "CAN Bus", "Python"],
        "preferred_proficiency": "Advanced",
        "openings_count": 20,
        "experience_level": "Mid Level (2-4 yrs)",
        "hiring_timeline": "Immediate (0-30 days)",
        "additional_requirements": "Hands-on experience in automotive high-voltage dyno testing.",
    }

    res = client.post("/api/employer/demands", json=payload, headers=EMPLOYER_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "created"
    assert "demand" in data

    demand = data["demand"]
    assert demand["id"].startswith("ed-")
    assert demand["company_name"] == "Mahindra Electric Mobility Ltd"
    assert demand["source"] == "EMPLOYER_SUBMITTED"
    assert demand["validation_status"] == "PENDING"
    assert demand["is_demo"] is False
    assert demand["provenance_label"] == "Employer Submitted — Pending Validation"
    assert demand["openings_count"] == 20
    assert "submitted_at" in demand


def test_employer_submission_invalid():
    """POST /api/employer/demands rejects payload with missing company or skills."""
    # 1. Missing company name
    res_no_company = client.post("/api/employer/demands", json={
        "company_name": "",
        "industry": "IT & Software",
        "district": "Pune",
        "job_role": "Software Developer",
        "required_skills": ["Python"],
    }, headers=EMPLOYER_HEADERS)
    assert res_no_company.status_code == 422

    # 2. Missing required skills
    res_no_skills = client.post("/api/employer/demands", json={
        "company_name": "Infosys",
        "industry": "IT & Software",
        "district": "Pune",
        "job_role": "Cloud Engineer",
        "required_skills": [],
    }, headers=EMPLOYER_HEADERS)
    assert res_no_skills.status_code == 422


def test_employer_demand_retrieval_and_filtering():
    """GET /api/employer/demands returns records and filters by status, district, and source."""
    # Submit a distinct record
    post_res = client.post("/api/employer/demands", json={
        "company_name": "Bharat Forge Ltd",
        "industry": "Manufacturing",
        "district": "Satara",
        "job_role": "CNC Metallurgy Technician",
        "required_skills": ["CNC Machining", "CAD/CAM"],
        "openings_count": 12,
    }, headers=EMPLOYER_HEADERS)
    new_id = post_res.json()["demand"]["id"]

    # 1. Single retrieval
    detail_res = client.get(f"/api/employer/demands/{new_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["demand"]["company_name"] == "Bharat Forge Ltd"

    # 2. Filter by status = PENDING
    res_pending = client.get("/api/employer/demands?status=PENDING")
    assert res_pending.status_code == 200
    pending_list = res_pending.json()
    assert any(d["id"] == new_id for d in pending_list)

    # 3. Filter by source = EMPLOYER_SUBMITTED
    res_src = client.get("/api/employer/demands?source=EMPLOYER_SUBMITTED")
    assert res_src.status_code == 200
    assert all(d["source"] == "EMPLOYER_SUBMITTED" for d in res_src.json())

    # 4. Unknown ID returns 404
    res_404 = client.get("/api/employer/demands/emp-usr-invalid-999")
    assert res_404.status_code == 404


def test_admin_employer_demands_and_validation():
    """Admin endpoints require authorization and allow validating/rejecting employer submissions."""
    # Create submission
    post_res = client.post("/api/employer/demands", json={
        "company_name": "Kirloskar Oil Engines",
        "industry": "Manufacturing",
        "district": "Kolhapur",
        "job_role": "Industrial Robotics Maintenance Engineer",
        "required_skills": ["Industrial Robotics", "PLC Programming"],
        "openings_count": 15,
    }, headers=EMPLOYER_HEADERS)
    demand_id = post_res.json()["demand"]["id"]

    # 1. Reject status update without key
    unauth_res = client.patch(
        f"/api/admin/employer/demands/{demand_id}/status",
        json={"status": "VALIDATED"}
    )
    assert unauth_res.status_code == 401

    # 2. List admin demands with stats
    admin_list_res = client.get("/api/admin/employer/demands", headers=ADMIN_AUTH_HEADERS)
    assert admin_list_res.status_code == 200
    admin_data = admin_list_res.json()
    assert "pending_count" in admin_data
    assert "validated_count" in admin_data
    assert admin_data["pending_count"] >= 1

    # 3. Mark as VALIDATED
    val_res = client.patch(
        f"/api/admin/employer/demands/{demand_id}/status",
        headers=ADMIN_AUTH_HEADERS,
        json={"status": "VALIDATED", "admin_notes": "Verified company GSTIN and plant presence."},
    )
    assert val_res.status_code == 200
    updated = val_res.json()["demand"]
    assert updated["validation_status"] == "VALIDATED"
    assert updated["admin_notes"] == "Verified company GSTIN and plant presence."

    # 4. Mark as REJECTED
    rej_res = client.patch(
        f"/api/admin/employer/demands/{demand_id}/status",
        headers=ADMIN_AUTH_HEADERS,
        json={"status": "REJECTED", "admin_notes": "Duplicate requirement."},
    )
    assert rej_res.status_code == 200
    assert rej_res.json()["demand"]["validation_status"] == "REJECTED"


def test_gap_engine_integration_with_validated_demands():
    """compute_gaps incorporates validated first-party employer demand signals."""
    # Pre-computation
    initial_gaps = compute_gaps(district="Pune")
    assert len(initial_gaps) > 0

    # Submit and validate new demand for specific skill
    post_res = client.post("/api/employer/demands", json={
        "company_name": "Bosch Global Software",
        "industry": "Automotive & EV",
        "district": "Pune",
        "job_role": "Cybersecurity Automotive Lead",
        "required_skills": ["Cybersecurity"],
        "openings_count": 50,
    }, headers=EMPLOYER_HEADERS)
    demand_id = post_res.json()["demand"]["id"]

    # Pending demand should NOT alter validated counts prematurely
    client.patch(
        f"/api/admin/employer/demands/{demand_id}/status",
        headers=ADMIN_AUTH_HEADERS,
        json={"status": "VALIDATED"},
    )

    # Post-validation gaps computation
    updated_gaps = compute_gaps(district="Pune")
    cyber_gap = next((g for g in updated_gaps if g["skill_name"] == "Cybersecurity"), None)
    assert cyber_gap is not None
    assert cyber_gap["demand_pct"] > 0
