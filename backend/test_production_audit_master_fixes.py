"""Production Audit Master Fixes Test Suite.

Verifies end-to-end fixes for:
1. Bug A: Student career recommendations (student_profiles user_id PK resolution, no 42703 column error).
2. Bug B: Student learning roadmap (student_profiles resolution without 42703 column error).
3. Bug C: Student industry & technology alerts (logger defined, student_id=me resolution, 200 OK).
4. Bug D: Employer hiring demand submission (no created_at PGRST204 mismatch, submitted_at canonical, PENDING status).
5. Bug E: Employer industry signals endpoint contract and data lifecycle.
6. Ownership, RBAC, and validation status isolation.
"""
import uuid
import pytest
from unittest.mock import patch
from starlette.testclient import TestClient

from app.main import app
from app.core.security import create_access_token
from app.db import init_db, init_demo_users
from app.repositories.supabase_repository import (
    get_student_profile,
    upsert_student_profile,
    create_employer_demand,
    get_employer_demand,
    delete_employer_demand_repo,
    create_student_assessment,
    delete_student_assessment_repo,
    SupabaseRepositoryError,
)

init_db()
init_demo_users()

client = TestClient(app)

STUDENT_TOKEN = create_access_token({
    "sub": "usr-student-001",
    "email": "student@skillsetu.gov.in",
    "role": "STUDENT",
})
STUDENT_HEADERS = {"Authorization": f"Bearer {STUDENT_TOKEN}"}

EMPLOYER_TOKEN = create_access_token({
    "sub": "usr-employer-001",
    "email": "employer@tcs.com",
    "role": "EMPLOYER",
    "organization_id": "org-tcs-001",
})
EMPLOYER_HEADERS = {"Authorization": f"Bearer {EMPLOYER_TOKEN}"}

ADMIN_TOKEN = create_access_token({
    "sub": "usr-admin-001",
    "email": "admin@skillsetu.gov.in",
    "role": "ADMIN",
})
ADMIN_HEADERS = {"Authorization": f"Bearer {ADMIN_TOKEN}"}


# =========================================================================
# 1. Bug A & B: Student Profile PK Resolution (No 'id' column assumption)
# =========================================================================

def test_student_profile_pk_resolution_no_42703_error():
    """Verify get_student_profile queries by user_id and does not crash when not found."""
    # Lookup non-existent student user_id
    non_existent = get_student_profile("usr-student-nonexistent-999")
    assert non_existent is None

    # Upsert with canonical schema columns
    saved = upsert_student_profile({
        "user_id": "usr-student-audit-001",
        "target_role": "AI Solutions Architect",
        "skill_match_pct": 82,
        "arbitrary_client_field": "should_be_stripped",
    })
    assert saved is not None
    assert saved["user_id"] == "usr-student-audit-001"
    assert saved["target_role"] == "AI Solutions Architect"

    # Fetch back
    fetched = get_student_profile("usr-student-audit-001")
    assert fetched is not None
    assert fetched["target_role"] == "AI Solutions Architect"


def test_student_career_recommendations_no_column_error():
    """Verify /api/student/recommendations/me succeeds with 200 and does not raise 42703."""
    resp = client.get("/api/student/recommendations/me", headers=STUDENT_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "recommended_careers" in data or "message" in data


def test_student_learning_roadmap_no_column_error():
    """Verify /api/student/me/roadmap succeeds with 200 and does not raise 42703."""
    resp = client.get("/api/student/me/roadmap", headers=STUDENT_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "roadmap" in data


# =========================================================================
# 2. Bug C: Student Industry Alerts (Logger defined, student_id=me resolved)
# =========================================================================

def test_student_industry_alerts_with_me_resolution():
    """Verify /api/student/industry-alerts?student_id=me succeeds without NameError logger."""
    resp = client.get("/api/student/industry-alerts?student_id=me", headers=STUDENT_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "alerts" in data
    assert isinstance(data["alerts"], list)

    # Domain filtering
    resp_ai = client.get("/api/student/industry-alerts?domain=ai_ml&student_id=me", headers=STUDENT_HEADERS)
    assert resp_ai.status_code == 200
    assert "alerts" in resp_ai.json()


# =========================================================================
# 3. Bug D: Employer Demand Submission (No created_at PGRST204 schema mismatch)
# =========================================================================

def test_employer_demand_submission_succeeds_without_created_at_mismatch():
    """Verify POST /api/employer/demand persists cleanly to Supabase with submitted_at."""
    payload = {
        "company_name": "Tata Consultancy Services",
        "industry": "IT & Software",
        "district": "Pune",
        "job_role": "Generative AI Lead",
        "required_skills": ["Generative AI", "RAG", "Python"],
        "openings_count": 10,
        "experience_level": "Entry Level (0-1 yrs)",
        "hiring_timeline": "Immediate (0-30 days)",
        "preferred_proficiency": "advanced",
    }
    resp = client.post("/api/employer/demand", json=payload, headers=EMPLOYER_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "created"
    demand = data["demand"]
    demand_id = demand["id"]

    try:
        # Confirm Supabase row exists authoritatively
        repo_item = get_employer_demand(demand_id)
        assert repo_item is not None
        assert repo_item["company_name"] == "Tata Consultancy Services"
        assert repo_item["validation_status"] == "PENDING"
        assert repo_item["submitted_at"] is not None
        assert repo_item.get("is_demo") is False
    finally:
        delete_employer_demand_repo(demand_id)


def test_employer_demand_repository_sanitization():
    """Verify create_employer_demand strips non-existent columns (created_at, etc.)."""
    raw_payload = {
        "id": f"dem-audit-{uuid.uuid4().hex[:8]}",
        "employer_id": "org-tcs-001",
        "company_name": "TCS Enterprise",
        "industry": "IT",
        "district": "Pune",
        "job_role": "Cloud Architect",
        "required_skills": ["AWS", "Kubernetes"],
        "created_at": "2026-09-03T00:00:00Z",  # Non-canonical column
        "status": "pending",                  # Non-canonical column
        "bogus_field": "strip_me",            # Unknown column
    }
    saved = create_employer_demand(raw_payload)
    demand_id = saved["id"]

    try:
        fetched = get_employer_demand(demand_id)
        assert fetched is not None
        assert fetched["validation_status"] == "PENDING"
        assert fetched["submitted_at"] is not None
    finally:
        delete_employer_demand_repo(demand_id)


# =========================================================================
# 4. Security & RBAC Enforcement
# =========================================================================

def test_employer_demand_security_rbac():
    """Verify unauthenticated returns 401, student returns 403."""
    payload = {
        "company_name": "Acme Corp",
        "industry": "Manufacturing",
        "district": "Pune",
        "job_role": "CNC Machinist",
        "required_skills": ["CNC"],
    }
    # Unauthenticated
    assert client.post("/api/employer/demand", json=payload).status_code in (401, 403)
    # Student forbidden
    assert client.post("/api/employer/demand", json=payload, headers=STUDENT_HEADERS).status_code in (401, 403)


# =========================================================================
# 5. Bug E: Signals Endpoint Contract
# =========================================================================

def test_signals_legacy_and_industry_endpoints():
    """Verify /api/signals and /api/industry/signals return proper arrays."""
    resp = client.get("/api/signals")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    resp_ind = client.get("/api/industry/signals")
    assert resp_ind.status_code == 200
    assert "signals" in resp_ind.json()


# =========================================================================
# 6. Admin Data Governance & Schemes Deduplication
# =========================================================================

def test_data_governance_counts_authoritative():
    """Verify data governance summary returns proper structure with authoritative counts."""
    from app.db import get_data_governance_summary
    gov = get_data_governance_summary()
    assert gov["status"] == "success"
    assert "tables" in gov
    assert "student_assessments" in gov["tables"]
    assert "employer_demands" in gov["tables"]
    assert "courses" in gov["tables"]
    assert "industry_signals" in gov["tables"]
    assert gov["tables"]["student_assessments"]["total"] >= 0


def test_schemes_recommendation_and_deduplication():
    """Verify /api/schemes/recommended/stu-001 succeeds with 200 and unique schemes."""
    resp = client.get("/api/schemes/recommended/stu-001")
    assert resp.status_code == 200
    data = resp.json()
    assert "schemes" in data
    schemes = data["schemes"]
    assert isinstance(schemes, list)
    # Check no duplicate scheme codes
    codes = [s.get("scheme_code") for s in schemes if s.get("scheme_code")]
    assert len(codes) == len(set(codes))

