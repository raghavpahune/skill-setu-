"""Phase 24 Test Suite: Secure Admin Board, RBAC Enforcement, & Data Provenance Integrity."""
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.db import init_db
from app.core.security import create_access_token

client = TestClient(app)


def get_token_for(user_id: str, role: str, email: str) -> str:
    return create_access_token({"sub": user_id, "role": role, "email": email})


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_admin_unauthenticated_endpoints_return_401():
    """All /api/admin/* endpoints strictly require authorization and reject anonymous calls with 401."""
    routes = [
        ("GET", "/api/admin/assessments"),
        ("GET", "/api/admin/assessments/stats/summary"),
        ("GET", "/api/admin/assessments/sa-001"),
        ("DELETE", "/api/admin/assessments/sa-001"),
        ("GET", "/api/admin/employer/demands"),
        ("PATCH", "/api/admin/employer/demands/ed-001/status"),
        ("DELETE", "/api/admin/employer/demands/ed-001"),
        ("GET", "/api/admin/gov/opportunities"),
        ("POST", "/api/admin/gov/opportunities"),
        ("PATCH", "/api/admin/gov/opportunities/gov-001"),
        ("DELETE", "/api/admin/gov/opportunities/gov-001"),
    ]

    for method, path in routes:
        if method == "GET":
            res = client.get(path)
        elif method == "POST":
            res = client.post(path, json={"name": "Test", "department": "Test"})
        elif method == "PATCH":
            res = client.patch(path, json={"status": "VALIDATED"})
        elif method == "DELETE":
            res = client.delete(path)
        assert res.status_code == 401, f"Expected 401 for anonymous {method} {path}, got {res.status_code}"


def test_admin_non_admin_roles_receive_403():
    """Authenticated users with STUDENT, EMPLOYER, INSTITUTE, or GOVERNMENT roles receive 403 Forbidden."""
    non_admin_roles = [
        ("usr-student-001", "STUDENT", "student@skillsetu.gov.in"),
        ("usr-employer-001", "EMPLOYER", "employer@skillsetu.gov.in"),
        ("usr-institute-001", "INSTITUTE", "institute@skillsetu.gov.in"),
        ("usr-gov-001", "GOVERNMENT", "government@skillsetu.gov.in"),
    ]

    for uid, role, email in non_admin_roles:
        token = get_token_for(uid, role, email)
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Assessment Registry
        res = client.get("/api/admin/assessments", headers=headers)
        assert res.status_code == 403, f"{role} should receive 403 on GET assessments"

        # 2. Assessment Stats
        res_stats = client.get("/api/admin/assessments/stats/summary", headers=headers)
        assert res_stats.status_code == 403, f"{role} should receive 403 on GET stats"

        # 3. Employer Demands Management
        res_emp = client.get("/api/admin/employer/demands", headers=headers)
        assert res_emp.status_code == 403, f"{role} should receive 403 on GET employer demands"

        # 4. Government Opportunities Management
        res_gov = client.get("/api/admin/gov/opportunities", headers=headers)
        assert res_gov.status_code == 403, f"{role} should receive 403 on GET gov opportunities"


def test_admin_bearer_token_authorized_access():
    """An authenticated ADMIN user with a valid JWT bearer token accesses all administrative endpoints."""
    admin_token = get_token_for("usr-admin-001", "ADMIN", "admin@skillsetu.gov.in")
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. List assessments
    res = client.get("/api/admin/assessments", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "success"
    assert "assessments" in res.json()

    # 2. Executive Stats
    res_stats = client.get("/api/admin/assessments/stats/summary", headers=headers)
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert "total_submissions" in stats
    assert "user_submitted_count" in stats
    assert "demo_synthetic_count" in stats
    assert "top_missing_skills" in stats
    assert "district_distribution" in stats

    # 3. Employer Demands
    res_emp = client.get("/api/admin/employer/demands", headers=headers)
    assert res_emp.status_code == 200
    assert "demands" in res_emp.json()

    # 4. Government Opportunities
    res_gov = client.get("/api/admin/gov/opportunities", headers=headers)
    assert res_gov.status_code == 200
    assert "opportunities" in res_gov.json()


def test_admin_provenance_separation_and_filtering():
    """Admin registry correctly separates and filters USER_SUBMITTED vs DEMO_SYNTHETIC records."""
    admin_token = get_token_for("usr-admin-001", "ADMIN", "admin@skillsetu.gov.in")
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create a real candidate submission
    cand_res = client.post("/api/student/assessment", json={
        "name": "Tanvi Joshi",
        "education": "B.Tech Computer Science",
        "district": "Pune",
        "career_goal": "AI Engineer",
        "interests": ["Machine Learning", "NLP"],
        "current_skills": [{"skill_name": "Python", "proficiency": "intermediate"}],
        "quiz_answers": {"q1": "a", "q2": "b"},
    })
    assert cand_res.status_code == 200
    cand_id = cand_res.json()["assessment"]["id"]

    # Filter by USER_SUBMITTED
    res_real = client.get("/api/admin/assessments?source=USER_SUBMITTED", headers=headers)
    assert res_real.status_code == 200
    real_records = res_real.json()["assessments"]
    assert any(r["id"] == cand_id for r in real_records)
    for r in real_records:
        assert r["source"] == "USER_SUBMITTED"

    # Filter by DEMO_SYNTHETIC
    res_demo = client.get("/api/admin/assessments?source=DEMO_SYNTHETIC", headers=headers)
    assert res_demo.status_code == 200
    demo_records = res_demo.json()["assessments"]
    assert not any(r["id"] == cand_id for r in demo_records)
    for r in demo_records:
        assert r["source"] == "DEMO_SYNTHETIC"


def test_admin_deletion_authorization():
    """Deleting records requires ADMIN authorization; unauthorized attempts fail with 401/403."""
    admin_token = get_token_for("usr-admin-001", "ADMIN", "admin@skillsetu.gov.in")
    student_token = get_token_for("usr-student-001", "STUDENT", "student@skillsetu.gov.in")

    # Create record to delete
    cand_res = client.post("/api/student/assessment", json={
        "name": "Record To Delete",
        "education": "Diploma",
        "district": "Nagpur",
        "career_goal": "EV Technician",
        "current_skills": [{"skill_name": "Soldering", "proficiency": "intermediate"}],
        "quiz_answers": {"q1": "a"},
    })
    assert cand_res.status_code == 200
    rec_id = cand_res.json()["assessment"]["id"]

    # 1. Anonymous delete -> 401
    res_anon = client.delete(f"/api/admin/assessments/{rec_id}")
    assert res_anon.status_code == 401

    # 2. Student delete -> 403
    res_stu = client.delete(f"/api/admin/assessments/{rec_id}", headers={"Authorization": f"Bearer {student_token}"})
    assert res_stu.status_code == 403

    # 3. Admin delete -> 200
    res_admin = client.delete(f"/api/admin/assessments/{rec_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin.status_code == 200
    assert res_admin.json()["deleted_id"] == rec_id

    # 4. Confirm deleted
    res_get = client.get(f"/api/admin/assessments/{rec_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_get.status_code == 404


def test_admin_employer_demand_validation_lifecycle():
    """Admin can audit, approve (VALIDATE), reject, and delete employer demands with authorization."""
    admin_token = get_token_for("usr-admin-001", "ADMIN", "admin@skillsetu.gov.in")
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Submit demand
    d_res = client.post("/api/employer/demands", json={
        "employer_name": "Tata Technologies Admin Test",
        "district": "Pune",
        "industry": "Automotive & EV",
        "job_role": "EV Battery Systems Engineer",
        "openings_count": 10,
        "required_skills": ["Battery Management Systems", "Thermal Analysis"],
    }, headers=headers)
    assert d_res.status_code == 200
    demand_id = d_res.json()["demand"]["id"]

    # Admin validates demand
    val_res = client.patch(
        f"/api/admin/employer/demands/{demand_id}/status",
        headers=headers,
        json={"status": "VALIDATED", "admin_notes": "Verified registered corporate entity."},
    )
    assert val_res.status_code == 200
    assert val_res.json()["demand"]["validation_status"] == "VALIDATED"
    assert val_res.json()["demand"]["admin_notes"] == "Verified registered corporate entity."

    # Admin deletes demand
    del_res = client.delete(f"/api/admin/employer/demands/{demand_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["deleted_id"] == demand_id


def test_admin_employer_demand_status_variations_and_rbac():
    """Detailed coverage of Employer Demand status updates:
    1. VALIDATED status
    2. REJECTED status
    3. admin_notes present
    4. admin_notes empty
    5. unauthorized / non-admin request
    6. malformed payload rejection
    """
    admin_token = get_token_for("usr-admin-001", "ADMIN", "admin@skillsetu.gov.in")
    student_token = get_token_for("usr-student-001", "STUDENT", "student@skillsetu.gov.in")
    admin_headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    student_headers = {"Authorization": f"Bearer {student_token}", "Content-Type": "application/json"}
    x_admin_headers = {"X-Admin-Key": "demo-admin-key-2026", "Content-Type": "application/json"}

    # Create demand
    d_res = client.post("/api/employer/demands", json={
        "employer_name": "Mahindra Electric Test",
        "district": "Nashik",
        "industry": "Automotive",
        "job_role": "High Voltage Power Specialist",
        "openings_count": 5,
        "required_skills": ["Power Electronics", "Inverter Design"],
    }, headers=admin_headers)
    assert d_res.status_code == 200
    demand_id = d_res.json()["demand"]["id"]

    # 1. Unauthorized / non-admin request -> 401 / 403
    unauth_res = client.patch(f"/api/admin/employer/demands/{demand_id}/status", json={"status": "VALIDATED"})
    assert unauth_res.status_code == 401

    stu_res = client.patch(f"/api/admin/employer/demands/{demand_id}/status", headers=student_headers, json={"status": "VALIDATED"})
    assert stu_res.status_code == 403

    # 2. VALIDATED with admin_notes present (via X-Admin-Key)
    val_res = client.patch(
        f"/api/admin/employer/demands/{demand_id}/status",
        headers=x_admin_headers,
        json={"status": "VALIDATED", "admin_notes": "Validated via quick admin action"},
    )
    assert val_res.status_code == 200
    assert val_res.json()["status"] == "success"
    assert val_res.json()["demand"]["validation_status"] == "VALIDATED"
    assert val_res.json()["demand"]["admin_notes"] == "Validated via quick admin action"

    # 3. REJECTED with admin_notes empty (via Bearer token)
    rej_res = client.patch(
        f"/api/admin/employer/demands/{demand_id}/status",
        headers=admin_headers,
        json={"status": "REJECTED", "admin_notes": ""},
    )
    assert rej_res.status_code == 200
    assert rej_res.json()["demand"]["validation_status"] == "REJECTED"
    assert rej_res.json()["demand"]["admin_notes"] == ""

    # 4. validation_status field synonym support
    syn_res = client.patch(
        f"/api/admin/employer/demands/{demand_id}/status",
        headers=admin_headers,
        json={"validation_status": "VALIDATED", "admin_notes": "Re-validated via synonym"},
    )
    assert syn_res.status_code == 200
    assert syn_res.json()["demand"]["validation_status"] == "VALIDATED"

    # 5. Malformed payload: invalid status value -> 422
    bad_val_res = client.patch(
        f"/api/admin/employer/demands/{demand_id}/status",
        headers=admin_headers,
        json={"status": "INVALID_STATUS_VALUE"},
    )
    assert bad_val_res.status_code == 422

    # 6. Malformed payload: missing status fields -> 422
    empty_body_res = client.patch(
        f"/api/admin/employer/demands/{demand_id}/status",
        headers=admin_headers,
        json={"admin_notes": "notes only without status"},
    )
    assert empty_body_res.status_code == 422


def test_admin_industry_signal_moderation_variations_and_rbac():
    """Detailed coverage of Industry Signal status updates:
    1. APPROVED validation status
    2. REJECTED validation status
    3. admin_notes present
    4. admin_notes empty
    5. unauthorized / non-admin request
    6. malformed payload rejection
    """
    admin_token = get_token_for("usr-admin-001", "ADMIN", "admin@skillsetu.gov.in")
    student_token = get_token_for("usr-student-001", "STUDENT", "student@skillsetu.gov.in")
    admin_headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    student_headers = {"Authorization": f"Bearer {student_token}", "Content-Type": "application/json"}
    x_admin_headers = {"X-Admin-Key": "demo-admin-key-2026", "Content-Type": "application/json"}

    # Get an existing signal or create one
    list_res = client.get("/api/admin/industry/signals", headers=admin_headers)
    assert list_res.status_code == 200
    signals = list_res.json()["signals"]
    assert len(signals) > 0
    signal_id = signals[0]["id"]

    # 1. Unauthorized / non-admin request -> 401 / 403
    unauth_res = client.patch(f"/api/admin/industry/signals/{signal_id}", json={"validation_status": "APPROVED"})
    assert unauth_res.status_code == 401

    stu_res = client.patch(f"/api/admin/industry/signals/{signal_id}", headers=student_headers, json={"validation_status": "APPROVED"})
    assert stu_res.status_code == 403

    # 2. APPROVED validation_status with empty admin_notes (via X-Admin-Key)
    app_res = client.patch(
        f"/api/admin/industry/signals/{signal_id}",
        headers=x_admin_headers,
        json={"validation_status": "APPROVED", "admin_notes": ""},
    )
    assert app_res.status_code == 200
    assert app_res.json()["status"] == "success"
    assert app_res.json()["signal"]["validation_status"] == "APPROVED"

    # 3. REJECTED validation_status with admin_notes present (via Bearer token)
    rej_res = client.patch(
        f"/api/admin/industry/signals/{signal_id}",
        headers=admin_headers,
        json={"validation_status": "REJECTED", "admin_notes": "Outdated industry trend."},
    )
    assert rej_res.status_code == 200
    assert rej_res.json()["signal"]["validation_status"] == "REJECTED"
    assert rej_res.json()["signal"]["admin_notes"] == "Outdated industry trend."

    # 4. is_active toggle
    toggle_res = client.patch(
        f"/api/admin/industry/signals/{signal_id}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert toggle_res.status_code == 200
    assert toggle_res.json()["signal"]["is_active"] is False

    # 5. Malformed payload: completely empty update dictionary -> 422
    empty_res = client.patch(
        f"/api/admin/industry/signals/{signal_id}",
        headers=admin_headers,
        json={},
    )
    assert empty_res.status_code == 422

    # 6. Non-existent signal ID -> 404
    not_found_res = client.patch(
        "/api/admin/industry/signals/non-existent-signal-id-99999",
        headers=admin_headers,
        json={"validation_status": "APPROVED"},
    )
    assert not_found_res.status_code == 404
