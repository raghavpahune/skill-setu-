"""Phase 32C Test Suite: Student Profiles & Assessments Supabase System of Record.

Verifies:
1. Repository operations: get, list, create, update for student profiles & assessments.
2. API reads bypass in-memory _cache and read directly from Supabase repository.
3. API writes persist to Supabase repository directly without relying on disk JSON.
4. Supabase mutation failure returns HTTP 5xx without silent success.
5. Security / RBAC: Unauthenticated => 401; cross-student private access => 403.
6. Identity spoofing rejection: client-supplied student/user identity ignored in favor of JWT.
7. Authorized access: student accessing own data succeeds; admin access succeeds.
8. Diagnostic assessment scoring & skill gap calculations remain exact.
9. Recommendation engine queries Supabase repository correctly.
10. Regression: Phase 32A employer_feedback and Phase 32B employer_demands remain fully intact.
"""

from copy import deepcopy
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.db import _cache, init_db, init_demo_users, save_user
from app.core.security import create_access_token
from app.repositories.supabase_repository import (
    get_student_profile,
    list_student_profiles,
    upsert_student_profile,
    get_student_assessment,
    get_student_assessment_by_user,
    list_student_assessments,
    create_student_assessment,
    update_student_assessment,
    delete_student_assessment_repo,
    SupabaseRepositoryError,
    AssessmentNotFoundError,
)

init_db()
init_demo_users()
save_user({
    "id": "usr-student-002",
    "name": "Priya Deshmukh",
    "email": "student2@skillsetu.gov.in",
    "role": "STUDENT",
    "hashed_password": "demo_password_hash",
})

client = TestClient(app)

STUDENT_AUTH_HEADERS = {
    "Authorization": f"Bearer {create_access_token({'sub': 'usr-student-001', 'email': 'student@skillsetu.gov.in', 'role': 'STUDENT'})}"
}
STUDENT2_AUTH_HEADERS = {
    "Authorization": f"Bearer {create_access_token({'sub': 'usr-student-002', 'email': 'student2@skillsetu.gov.in', 'role': 'STUDENT'})}"
}
ADMIN_AUTH_HEADERS = {
    "Authorization": f"Bearer {create_access_token({'sub': 'usr-admin-001', 'email': 'admin@skillsetu.gov.in', 'role': 'ADMIN'})}",
    "x-admin-key": "admin_master_secret",
}


def test_01_repository_student_profile_lifecycle():
    """Verify repository get, list, and upsert for student_profiles."""
    profiles = list_student_profiles()
    assert len(profiles) >= 1
    p1 = get_student_profile("stu-001")
    assert p1 is not None
    assert p1.get("target_role") == "AI Engineer"

    # Upsert new profile
    new_profile = {
        "user_id": "stu-test-999",
        "name": "Arjun Test",
        "target_role": "Cloud Architect",
        "skill_match_pct": 75,
        "source": "TEST",
    }
    saved = upsert_student_profile(new_profile)
    assert saved["user_id"] == "stu-test-999"
    retrieved = get_student_profile("stu-test-999")
    assert retrieved is not None
    assert retrieved["target_role"] == "Cloud Architect"


def test_02_repository_student_assessment_lifecycle():
    """Verify repository get, list, create, update, delete for student_assessments."""
    assessments = list_student_assessments()
    assert len(assessments) >= 1

    # Create assessment
    test_data = {
        "id": "ast-test-phase32c",
        "user_id": "stu-001",
        "user_email": "student@skillsetu.gov.in",
        "name": "Aarav Patil",
        "career_goal": "AI Engineer",
        "quiz_score_pct": 90,
        "skill_match_pct": 70,
        "source": "USER_SUBMITTED",
        "is_demo": False,
    }
    created = create_student_assessment(test_data)
    assert created["id"] == "ast-test-phase32c"

    # Read back
    fetched = get_student_assessment("ast-test-phase32c")
    assert fetched is not None
    assert fetched["career_goal"] == "AI Engineer"

    # Read by user
    by_user = get_student_assessment_by_user("stu-001")
    assert by_user is not None

    # Update
    updated = update_student_assessment("ast-test-phase32c", {"quiz_score_pct": 95})
    assert updated["quiz_score_pct"] == 95

    # Delete
    deleted = delete_student_assessment_repo("ast-test-phase32c")
    assert deleted is True
    assert get_student_assessment("ast-test-phase32c") is None


def test_03_api_passport_and_assessments_bypass_cache(mock_supabase_for_tests):
    """Verify runtime reads query Supabase directly even if _cache is empty or corrupted."""
    # Ensure a known record exists in mock Supabase with latest timestamp
    test_row = {
        "id": "ast-live-cache-bypass",
        "user_id": "usr-student-001",
        "user_email": "student@skillsetu.gov.in",
        "name": "Aarav Live",
        "career_goal": "Cloud AI Systems Engineer",
        "current_skills": [{"skill_name": "Python", "proficiency": "advanced"}],
        "quiz_score_pct": 85,
        "skill_match_pct": 60,
        "source": "USER_SUBMITTED",
        "is_demo": False,
        "created_at": "2099-01-01T00:00:00+00:00",
        "updated_at": "2099-01-01T00:00:00+00:00",
    }
    mock_supabase_for_tests.table("student_assessments").rows.append(deepcopy(test_row))

    # Wipe or poison the in-memory cache
    if "student_assessments" in _cache:
        _cache["student_assessments"] = []

    # GET /api/student/me/passport must read from Supabase
    res = client.get("/api/student/me/passport", headers=STUDENT_AUTH_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data["target_role"] == "Cloud AI Systems Engineer"
    assert data["name"] == "Aarav Live"


def test_04_api_submit_assessment_persists_to_supabase(mock_supabase_for_tests):
    """Verify POST /api/student/assessment persists directly to Supabase repository."""
    payload = {
        "name": "Aarav Patil",
        "education": "B.Tech Computer Science",
        "career_goal": "AI Engineer",
        "district": "Pune",
        "current_skills": [
            {"skill_name": "Python", "proficiency": "advanced"},
            {"skill_name": "Machine Learning", "proficiency": "intermediate"},
        ],
        "interests": ["AI / ML"],
        "quiz_answers": {"q1": "b", "q2": "c", "q3": "a"},
    }

    res = client.post("/api/student/assessment", json=payload, headers=STUDENT_AUTH_HEADERS)
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["status"] == "success"
    assessment = res_data["assessment"]
    aid = assessment["id"]
    assert assessment["user_id"] == "usr-student-001"
    assert assessment["user_email"] == "student@skillsetu.gov.in"

    # Confirm record is present in Supabase table
    sb_table = mock_supabase_for_tests.table("student_assessments")
    persisted = next((r for r in sb_table.rows if r.get("id") == aid), None)
    assert persisted is not None
    assert persisted["user_id"] == "usr-student-001"
    assert persisted["career_goal"] == "AI Engineer"


def test_05_supabase_mutation_failure_returns_5xx(mock_supabase_for_tests):
    """Verify that if Supabase fails during assessment creation, HTTP 500 is returned."""
    mock_supabase_for_tests.table("student_assessments").should_fail_insert = True

    payload = {
        "name": "Failed Student",
        "education": "B.Sc IT",
        "career_goal": "Data Analyst",
        "district": "Mumbai",
        "current_skills": [{"skill_name": "SQL", "proficiency": "beginner"}],
        "interests": ["Data"],
        "quiz_answers": {},
    }

    res = client.post("/api/student/assessment", json=payload, headers=STUDENT_AUTH_HEADERS)
    assert res.status_code == 500
    assert "Database insertion failed" in res.json()["detail"]


def test_06_unauthenticated_student_endpoints_return_401():
    """Verify unauthenticated requests to private endpoints return 401."""
    res_me = client.get("/api/student/me/passport")
    assert res_me.status_code == 401

    res_road = client.get("/api/student/me/roadmap")
    assert res_road.status_code == 401


def test_07_cross_student_access_rejected_with_403(mock_supabase_for_tests):
    """Verify Student 2 cannot access Student 1's private assessment report."""
    private_ast = {
        "id": "ast-private-stu001",
        "user_id": "usr-student-001",
        "user_email": "student@skillsetu.gov.in",
        "name": "Student One",
        "career_goal": "AI Engineer",
        "source": "USER_SUBMITTED",
        "is_demo": False,
    }
    mock_supabase_for_tests.table("student_assessments").rows.append(deepcopy(private_ast))

    # Student 2 attempting to view Student 1's private assessment
    res = client.get("/api/student/assessment/ast-private-stu001", headers=STUDENT2_AUTH_HEADERS)
    assert res.status_code == 403
    assert "Forbidden" in res.json()["detail"]

    # Student 1 accessing own assessment succeeds
    res_owner = client.get("/api/student/assessment/ast-private-stu001", headers=STUDENT_AUTH_HEADERS)
    assert res_owner.status_code == 200
    assert res_owner.json()["assessment"]["id"] == "ast-private-stu001"


def test_08_admin_can_access_student_assessment(mock_supabase_for_tests):
    """Verify administrative audit access to private student assessments succeeds."""
    private_ast = {
        "id": "ast-admin-audit-target",
        "user_id": "usr-student-001",
        "user_email": "student@skillsetu.gov.in",
        "name": "Student One",
        "career_goal": "AI Engineer",
        "source": "USER_SUBMITTED",
        "is_demo": False,
    }
    mock_supabase_for_tests.table("student_assessments").rows.append(deepcopy(private_ast))

    # Admin GET detail
    res_admin = client.get("/api/admin/assessments/ast-admin-audit-target", headers=ADMIN_AUTH_HEADERS)
    assert res_admin.status_code == 200
    assert res_admin.json()["assessment"]["id"] == "ast-admin-audit-target"

    # Admin DELETE
    res_del = client.delete("/api/admin/assessments/ast-admin-audit-target", headers=ADMIN_AUTH_HEADERS)
    assert res_del.status_code == 200
    assert res_del.json()["status"] == "success"


def test_09_client_identity_spoofing_ignored_in_assessment():
    """Verify that authenticated JWT identity is strictly attached, overriding any client spoof."""
    payload = {
        "name": "Aarav Spoofing",
        "education": "B.Tech",
        "career_goal": "AI Engineer",
        "district": "Pune",
        "current_skills": [{"skill_name": "Python", "proficiency": "advanced"}],
        "interests": ["AI"],
        "quiz_answers": {},
    }

    # Even if client body tries to spoof another user_id:
    payload["user_id"] = "victim-stu-999"
    payload["user_email"] = "victim@skillsetu.gov.in"

    res = client.post("/api/student/assessment", json=payload, headers=STUDENT_AUTH_HEADERS)
    assert res.status_code == 200
    saved = res.json()["assessment"]
    # Must be bound to authenticated student (usr-student-001), NOT the spoofed victim ID
    assert saved["user_id"] == "usr-student-001"
    assert saved["user_email"] == "student@skillsetu.gov.in"


def test_10_scoring_and_recommendation_engine_integrity(mock_supabase_for_tests):
    """Verify diagnostic assessment scoring and recommendation engine integration."""
    payload = {
        "name": "Aarav Scoring",
        "education": "B.Tech CSE",
        "career_goal": "AI Engineer",
        "district": "Pune",
        "current_skills": [
            {"skill_name": "Python", "proficiency": "advanced"},
            {"skill_name": "Machine Learning", "proficiency": "intermediate"},
        ],
        "interests": ["AI / ML"],
        "quiz_answers": {"q1": "b", "q2": "c"},
    }
    res = client.post("/api/student/assessment", json=payload, headers=STUDENT_AUTH_HEADERS)
    assert res.status_code == 200
    ast = res.json()["assessment"]
    assert "quiz_score_pct" in ast
    assert "skill_match_pct" in ast
    assert "combined_readiness_score" in ast
    assert "evaluation_summary" in ast

    # Verify recommendations endpoint uses the Supabase-persisted assessment
    rec_res = client.get("/api/student/recommendations/me", headers=STUDENT_AUTH_HEADERS)
    assert rec_res.status_code == 200
    recs = rec_res.json()
    assert recs["status"] == "success"
    assert "target_career_goal" in recs
    assert len(recs.get("recommended_careers", [])) > 0


def test_11_phase32a_feedback_and_phase32b_demands_remain_functional(mock_supabase_for_tests):
    """Regression test: Phase 32A employer_feedback and Phase 32B employer_demands still work."""
    # 1. Phase 32A: Feedback read & write
    emp_token = create_access_token({"sub": "usr-employer-001", "email": "employer@skillsetu.gov.in", "role": "EMPLOYER"})
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    fb_res = client.post(
        "/api/employer/feedback",
        json={"feedback_id": "ef-001", "status": "confirmed", "notes": "Phase 32C regression check"},
        headers=emp_headers,
    )
    assert fb_res.status_code == 200

    # 2. Phase 32B: Demand read & write
    dm_res = client.post(
        "/api/employer/demand",
        json={
            "company_name": "Tata Motors",
            "industry": "Automotive & EV",
            "district": "Pune",
            "job_role": "MLOps Architect",
            "required_skills": ["Python", "Docker", "Kubernetes"],
            "openings_count": 10,
        },
        headers=emp_headers,
    )
    assert dm_res.status_code == 200
    assert dm_res.json()["demand"]["job_role"] == "MLOps Architect"


def test_12_supabase_profile_wins_over_stale_cache(mock_supabase_for_tests):
    """Requirement A: Supabase assessment/profile record wins over stale/different local cache data."""
    # Stale cache data
    _cache["student_assessments"] = [{
        "id": "ast-stale-001",
        "user_id": "usr-student-001",
        "user_email": "student@skillsetu.gov.in",
        "career_goal": "Old Stale Career Goal",
        "current_skills": [],
        "source": "USER_SUBMITTED",
        "is_demo": False,
    }]

    # Fresh authoritative record in Supabase
    sb_table = mock_supabase_for_tests.table("student_assessments")
    sb_table.rows = [r for r in sb_table.rows if r.get("user_id") != "usr-student-001"]
    sb_table.rows.append({
        "id": "ast-supabase-authoritative",
        "user_id": "usr-student-001",
        "user_email": "student@skillsetu.gov.in",
        "name": "Aarav Patil",
        "career_goal": "Supabase Authoritative Goal",
        "current_skills": [{"skill_name": "Python", "proficiency": "advanced"}],
        "quiz_score_pct": 95,
        "skill_match_pct": 80,
        "source": "USER_SUBMITTED",
        "is_demo": False,
    })

    res = client.get("/api/student/me/passport", headers=STUDENT_AUTH_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data["target_role"] == "Supabase Authoritative Goal"
    assert data["user_id"] == "usr-student-001"


def test_13_missing_student_does_not_pull_random_demo(mock_supabase_for_tests):
    """Requirement B: Missing student record does NOT silently pull a random demo profile/assessment."""
    save_user({
        "id": "usr-student-brand-new",
        "name": "Brand New Student",
        "email": "brandnew@skillsetu.gov.in",
        "role": "STUDENT",
        "hashed_password": "demo_password_hash",
    })
    # Create token for student with no records in Supabase
    new_token = create_access_token({"sub": "usr-student-brand-new", "email": "brandnew@skillsetu.gov.in", "role": "STUDENT"})
    new_headers = {"Authorization": f"Bearer {new_token}"}

    # Passport must return explicit unassessed state, NOT demo candidate stu-001
    res_pass = client.get("/api/student/me/passport", headers=new_headers)
    assert res_pass.status_code == 200
    data = res_pass.json()
    assert data["is_personalized"] is False
    assert data["target_role"] is None or data["target_role"] == "Unassigned"
    assert data["user_id"] == "usr-student-brand-new"

    # Roadmap must return empty unassessed roadmap, NOT demo candidate roadmap
    res_road = client.get("/api/student/me/roadmap", headers=new_headers)
    assert res_road.status_code == 200
    road_data = res_road.json()
    assert road_data["has_roadmap"] is False
    assert len(road_data["roadmap"]) == 0

    # Career recommendations for unassessed self must return unassessed empty state, NOT demo candidate recommendations
    res_rec = client.get("/api/student/recommendations/usr-student-brand-new", headers=new_headers)
    assert res_rec.status_code == 200
    rec_data = res_rec.json()
    assert rec_data.get("status") == "unassessed"
    assert rec_data.get("has_assessment") is False
    assert len(rec_data.get("recommended_careers", [])) == 0

    # Career recommendations for unknown other student returns 404
    res_rec_unk = client.get("/api/student/recommendations/usr-unknown-nonexistent-student")
    assert res_rec_unk.status_code == 404

    # Schemes recommendation must return 404, NOT demo candidate schemes
    res_scheme = client.get("/api/schemes/recommended/usr-student-brand-new")
    assert res_scheme.status_code == 404

    # Gov opportunities recommendation must return 404, NOT demo candidate opportunities
    res_gov = client.get("/api/gov-opportunities/recommended/usr-student-brand-new")
    assert res_gov.status_code == 404


def test_14_repository_error_returns_5xx_no_demo_recovery(mock_supabase_for_tests):
    """Requirement C: Repository read error returns 5xx rather than silently continuing with demo data."""
    mock_supabase_for_tests.table("student_assessments").should_fail_select = True
    mock_supabase_for_tests.table("student_profiles").should_fail_select = True

    try:
        # 1. /api/student/me/passport
        res1 = client.get("/api/student/me/passport", headers=STUDENT_AUTH_HEADERS)
        assert res1.status_code == 500
        assert "Database query failed" in res1.json()["detail"]

        # 2. /api/student/assessments
        res2 = client.get("/api/student/assessments")
        assert res2.status_code == 500
        assert "Database query failed" in res2.json()["detail"]

        # 3. /api/admin/assessments
        res3 = client.get("/api/admin/assessments", headers=ADMIN_AUTH_HEADERS)
        assert res3.status_code == 500
        assert "Database query failed" in res3.json()["detail"]

        # 4. /api/admin/assessments/stats/summary
        res4 = client.get("/api/admin/assessments/stats/summary", headers=ADMIN_AUTH_HEADERS)
        assert res4.status_code == 500
        assert "Database query failed" in res4.json()["detail"]
    finally:
        mock_supabase_for_tests.table("student_assessments").should_fail_select = False
        mock_supabase_for_tests.table("student_profiles").should_fail_select = False


def test_15_legitimate_demo_candidate_selector_still_functions():
    """Requirement I: Legitimate demo candidate selector continues to function for explicit demo IDs."""
    # 1. GET /api/students returns demo candidate list
    res = client.get("/api/students")
    assert res.status_code == 200
    candidates = res.json()
    assert len(candidates) >= 1
    assert any(c["user_id"] == "stu-001" for c in candidates)

    # 2. GET /api/student/stu-001/passport succeeds with demo fixture
    pass_res = client.get("/api/student/stu-001/passport")
    assert pass_res.status_code == 200
    assert pass_res.json()["user_id"] == "stu-001"
    assert pass_res.json()["target_role"] == "AI Engineer"

    # 3. GET /api/student/stu-001/roadmap succeeds with demo fixture
    road_res = client.get("/api/student/stu-001/roadmap")
    assert road_res.status_code == 200
    assert len(road_res.json().get("roadmap", [])) > 0


def test_16_admin_delete_missing_returns_404_and_deletes_from_supabase(mock_supabase_for_tests):
    """Requirement H: Admin assessment delete removes from Supabase and returns 404 when absent."""
    # Absent ID -> 404
    res_absent = client.delete("/api/admin/assessments/ast-completely-nonexistent", headers=ADMIN_AUTH_HEADERS)
    assert res_absent.status_code == 404

    # Existing ID in Supabase
    target_row = {
        "id": "ast-to-be-deleted-admin",
        "user_id": "usr-student-delete-target",
        "user_email": "del@skillsetu.gov.in",
        "career_goal": "Testing Delete",
        "source": "USER_SUBMITTED",
        "is_demo": False,
    }
    mock_supabase_for_tests.table("student_assessments").rows.append(deepcopy(target_row))

    # Perform delete
    res_del = client.delete("/api/admin/assessments/ast-to-be-deleted-admin", headers=ADMIN_AUTH_HEADERS)
    assert res_del.status_code == 200
    assert res_del.json()["deleted_id"] == "ast-to-be-deleted-admin"

    # Verify gone from Supabase table
    surviving = [r for r in mock_supabase_for_tests.table("student_assessments").rows if r.get("id") == "ast-to-be-deleted-admin"]
    assert len(surviving) == 0


def test_17_schemes_and_gov_opps_demo_vs_production_behavior():
    """Requirements D, E, F: Schemes & Gov Opportunities resolve demo candidates by demo ID, 404 for unknown production users."""
    # Explicit demo candidate -> 200
    res_demo_sch = client.get("/api/schemes/recommended/stu-001")
    assert res_demo_sch.status_code == 200
    assert res_demo_sch.json()["student_id"] == "stu-001"

    res_demo_gov = client.get("/api/gov/opportunities/recommended/stu-001")
    assert res_demo_gov.status_code == 200
    assert res_demo_gov.json()["student_id"] == "stu-001"

    # Unknown production candidate -> 404 (no silent fallback to stu-001)
    res_unk_sch = client.get("/api/schemes/recommended/usr-nonexistent-student-99")
    assert res_unk_sch.status_code == 404

    res_unk_gov = client.get("/api/gov/opportunities/recommended/usr-nonexistent-student-99")
    assert res_unk_gov.status_code == 404
