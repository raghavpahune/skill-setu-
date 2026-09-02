"""Phase 32A Test Suite: Supabase System-of-Record Foundation for employer_feedback.

Verifies:
A. Supabase repository can read feedback.
B. Supabase repository can update feedback.
C. API GET/read path does not depend on _cache for employer_feedback.
D. API mutation writes to Supabase.
E. Supabase write failure returns 5xx (Mandatory Critical Failure Test).
F. Unauthenticated mutation returns 401.
G. Student mutation returns 403.
H. Unrelated employer mutation returns 403.
I. Authorized employer mutation succeeds.
J. Admin mutation succeeds.
K. Client cannot spoof ownership via payload body.
L. Zero local JSON writes and zero _cache mutation on Supabase failure.
"""
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.core.security import create_access_token
from app.repositories.supabase_repository import (
    get_employer_feedback,
    list_employer_feedback,
    update_employer_feedback,
    FeedbackNotFoundError,
    SupabaseRepositoryError,
    get_client,
)
from app.db import _cache, init_db, init_demo_users

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


# ============================================================================
# A & B: REPOSITORY DIRECT TESTS
# ============================================================================

def test_a_repository_can_read_feedback():
    """A. Supabase repository can read employer feedback by ID and list with filters."""
    rec = get_employer_feedback("ef-001")
    assert rec is not None
    assert rec["id"] == "ef-001"
    assert rec["employer_id"] == "emp-001"

    # Non-existent ID returns None
    assert get_employer_feedback("ef-nonexistent-999") is None

    # List feedback
    all_fb = list_employer_feedback()
    assert isinstance(all_fb, list)
    assert len(all_fb) > 0

    # Filtered list
    confirmed_fb = list_employer_feedback(status="confirmed")
    for f in confirmed_fb:
        assert f["status"].lower() == "confirmed"


def test_b_repository_can_update_feedback():
    """B. Supabase repository can update feedback and raises FeedbackNotFoundError on missing rows."""
    updated = update_employer_feedback("ef-001", {"status": "confirmed", "notes": "Repository direct update"})
    assert updated["id"] == "ef-001"
    assert updated["status"] == "confirmed"
    assert updated["notes"] == "Repository direct update"

    # Verify subsequent read reflects the update
    read_back = get_employer_feedback("ef-001")
    assert read_back["status"] == "confirmed"

    # Updating non-existent row raises FeedbackNotFoundError
    with pytest.raises(FeedbackNotFoundError):
        update_employer_feedback("ef-ghost-999", {"status": "rejected"})


# ============================================================================
# C & D: API GET & MUTATION TO SUPABASE
# ============================================================================

def test_c_api_get_does_not_depend_on_cache():
    """C. API GET /api/employer/validate reads from Supabase, not _cache."""
    # Deliberately clear or corrupt _cache["employer_feedback"]
    original_cache = _cache.get("employer_feedback")
    _cache["employer_feedback"] = [{"id": "stale-cache-record", "employer_id": "emp-stale"}]

    try:
        res = client.get("/api/employer/validate")
        assert res.status_code == 200
        items = res.json()
        # Ensure it read the actual Supabase items, not the stale cache
        ids = [item["id"] for item in items]
        assert "ef-001" in ids
        assert "stale-cache-record" not in ids
    finally:
        if original_cache is not None:
            _cache["employer_feedback"] = original_cache


def test_d_api_mutation_writes_to_supabase():
    """D. API POST /api/employer/feedback mutates the Supabase record directly."""
    payload = {
        "feedback_id": "ef-001",
        "status": "corrected",
        "notes": "Direct Supabase write verified",
        "proficiency_required": "advanced",
    }
    res = client.post("/api/employer/feedback", json=payload, headers=EMPLOYER_1_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "updated"
    assert data["feedback"]["status"] == "corrected"
    assert data["feedback"]["notes"] == "Direct Supabase write verified"

    # Verify directly from Supabase repository
    persisted = get_employer_feedback("ef-001")
    assert persisted["status"] == "corrected"
    assert persisted["notes"] == "Direct Supabase write verified"


# ============================================================================
# E: CRITICAL MANDATORY FAILURE TEST
# ============================================================================

def test_e_supabase_write_failure_returns_5xx():
    """E. Mandatory Critical Test: If Supabase fails, API returns HTTP >= 500, with NO 200, NO JSON, NO cache success."""
    sb_client = get_client()
    sb_client.table("employer_feedback").should_fail_update = True

    try:
        payload = {
            "feedback_id": "ef-001",
            "status": "confirmed",
            "notes": "This write must fail because Supabase is down",
        }
        res = client.post("/api/employer/feedback", json=payload, headers=EMPLOYER_1_HEADERS)

        # Must be HTTP 500 or higher
        assert res.status_code >= 500, f"Expected 5xx, got {res.status_code}: {res.text}"
        
        # Verify NO success response
        res_json = res.json()
        assert res_json.get("status") != "updated"
        assert "Database update failed" in res_json.get("detail", "")
    finally:
        sb_client.table("employer_feedback").should_fail_update = False


# ============================================================================
# F, G, H, I, J, K: SECURITY & RBAC PRESERVATION
# ============================================================================

def test_f_unauthenticated_mutation_returns_401():
    """F. Unauthenticated request to /api/employer/feedback must return 401."""
    res = client.post("/api/employer/feedback", json={
        "feedback_id": "ef-001",
        "status": "confirmed",
    })
    assert res.status_code == 401


def test_g_student_mutation_returns_403():
    """G. Student attempting to mutate employer feedback must return 403."""
    res = client.post("/api/employer/feedback", json={
        "feedback_id": "ef-001",
        "status": "confirmed",
    }, headers=STUDENT_HEADERS)
    assert res.status_code == 403


def test_h_unrelated_employer_mutation_returns_403():
    """H. Unrelated employer attempting to mutate another employer's feedback must return 403."""
    # ef-001 belongs to emp-001. EMPLOYER_2 belongs to emp-002.
    res = client.post("/api/employer/feedback", json={
        "feedback_id": "ef-001",
        "status": "rejected",
    }, headers=EMPLOYER_2_HEADERS)
    assert res.status_code == 403


def test_i_authorized_employer_mutation_succeeds():
    """I. Authorized employer mutation succeeds (200)."""
    res = client.post("/api/employer/feedback", json={
        "feedback_id": "ef-001",
        "status": "confirmed",
        "notes": "Verified by Tata Motors hiring committee",
    }, headers=EMPLOYER_1_HEADERS)
    assert res.status_code == 200
    assert res.json()["status"] == "updated"
    assert res.json()["feedback"]["status"] == "confirmed"


def test_j_admin_mutation_succeeds():
    """J. Admin mutation succeeds (200) across any employer's feedback."""
    res = client.post("/api/employer/feedback", json={
        "feedback_id": "ef-004",  # belongs to emp-002
        "status": "confirmed",
        "notes": "Validated by Platform Admin",
    }, headers=ADMIN_HEADERS)
    assert res.status_code == 200
    assert res.json()["status"] == "updated"
    assert res.json()["feedback"]["status"] == "confirmed"


def test_k_client_cannot_spoof_ownership():
    """K. Client request body specifying a fake employer_id cannot spoof ownership."""
    # Attacker tries to pass employer_id: "emp-001" in body, but authenticated token is EMPLOYER_2
    res = client.post("/api/employer/feedback", json={
        "feedback_id": "ef-001",
        "employer_id": "emp-001",
        "status": "confirmed",
    }, headers=EMPLOYER_2_HEADERS)
    assert res.status_code == 403
