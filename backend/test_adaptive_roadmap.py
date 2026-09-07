import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token
from app.repositories import supabase_repository
from app.services.roadmap_service import compute_adaptive_roadmap


@pytest.fixture(autouse=True)
def stub_upsert_student_roadmap(monkeypatch):
    monkeypatch.setattr(supabase_repository, "upsert_student_roadmap", lambda data: data)


def test_topological_dag_ordering_ai_engineer():
    result = compute_adaptive_roadmap("stu-001", target_role="AI Engineer", is_demo=True)
    assert result["has_roadmap"] is True
    steps = result["roadmap"]
    assert len(steps) >= 5

    sids = [s["skill_id"] for s in steps]
    if "sk-001" in sids and "sk-002" in sids:
        assert sids.index("sk-001") < sids.index("sk-002")
    if "sk-002" in sids and "sk-003" in sids:
        assert sids.index("sk-002") < sids.index("sk-003")
    if "sk-003" in sids and "sk-004" in sids:
        assert sids.index("sk-003") < sids.index("sk-004")

    last_step = steps[-1]
    assert last_step["status"] == "PROJECT"
    assert "deliverables" in last_step
    assert len(last_step["deliverables"]) >= 2


def test_adaptive_status_classification(monkeypatch):
    mock_profile = {
        "user_id": "usr-adaptive-test",
        "target_role": "Data Analyst",
        "skills": [
            {"skill_id": "sk-001", "proficiency": "advanced"},
            {"skill_id": "sk-008", "proficiency": "beginner"},
        ],
    }
    monkeypatch.setattr(supabase_repository, "get_student_profile", lambda uid: mock_profile if uid == "usr-adaptive-test" else None)
    monkeypatch.setattr(supabase_repository, "get_student_assessment_by_user", lambda uid: None)
    monkeypatch.setattr(supabase_repository, "get_student_assessment", lambda aid: None)

    result = compute_adaptive_roadmap("usr-adaptive-test", is_demo=False)
    assert result["has_roadmap"] is True
    steps = result["roadmap"]

    py_step = next((s for s in steps if s["skill_id"] == "sk-001"), None)
    assert py_step is not None
    assert py_step["status"] == "SKIP"
    assert py_step["estimated_hours"] == 0

    sql_step = next((s for s in steps if s["skill_id"] == "sk-008"), None)
    assert sql_step is not None
    assert sql_step["status"] == "REVIEW"
    assert sql_step["estimated_hours"] > 0

    missing_steps = [s for s in steps if s["status"] == "LEARN"]
    assert len(missing_steps) >= 1
    assert result["readiness_score"] > 0
    assert result["summary"]["skipped"] >= 1
    assert result["summary"]["to_review"] >= 1
    assert result["summary"]["to_learn"] >= 1
    assert result["summary"]["projects"] == 1


def test_unassessed_real_student_returns_empty_roadmap(monkeypatch):
    monkeypatch.setattr(supabase_repository, "get_student_profile", lambda uid: None)
    monkeypatch.setattr(supabase_repository, "get_student_assessment_by_user", lambda uid: None)
    monkeypatch.setattr(supabase_repository, "get_student_assessment", lambda aid: None)

    result = compute_adaptive_roadmap("usr-completely-new-student", is_demo=False)
    assert result["has_roadmap"] is False
    assert len(result["roadmap"]) == 0
    assert result["readiness_score"] == 0


from app.db import save_user


def test_roadmap_endpoint_authentication_and_idor(monkeypatch):
    save_user({"id": "usr-other-intruder", "email": "intruder@gov.in", "role": "STUDENT", "full_name": "Intruder User"})
    save_user({"id": "usr-protected-student", "email": "owner@gov.in", "role": "STUDENT", "full_name": "Owner User"})

    mock_profile = {
        "user_id": "usr-protected-student",
        "target_role": "Cybersecurity Analyst",
        "skills": [{"skill_id": "sk-001", "proficiency": "advanced"}],
    }
    monkeypatch.setattr(supabase_repository, "get_student_profile", lambda uid: mock_profile if uid == "usr-protected-student" else None)
    monkeypatch.setattr(supabase_repository, "get_student_assessment_by_user", lambda uid: None)

    with TestClient(app) as c:
        unauth = c.get("/api/student/usr-protected-student/roadmap")
        assert unauth.status_code == 401

        other_token = create_access_token({"sub": "usr-other-intruder", "email": "intruder@gov.in", "role": "STUDENT"})
        forbidden = c.get(
            "/api/student/usr-protected-student/roadmap",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert forbidden.status_code == 403

        owner_token = create_access_token({"sub": "usr-protected-student", "email": "owner@gov.in", "role": "STUDENT"})
        success = c.get(
            "/api/student/usr-protected-student/roadmap",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert success.status_code == 200
        body = success.json()
        assert body["has_roadmap"] is True
        assert body["target_role"] == "Cybersecurity Analyst"


def test_recalculate_roadmap_endpoint(monkeypatch):
    save_user({"id": "usr-recalc-student", "email": "recalc@gov.in", "role": "STUDENT", "full_name": "Recalc Student"})

    state = {
        "skills": [{"skill_id": "sk-001", "proficiency": "beginner"}]
    }

    def get_profile(uid):
        if uid == "usr-recalc-student":
            return {"user_id": uid, "target_role": "AI Engineer", "skills": state["skills"]}
        return None

    monkeypatch.setattr(supabase_repository, "get_student_profile", get_profile)
    monkeypatch.setattr(supabase_repository, "get_student_assessment_by_user", lambda uid: None)

    with TestClient(app) as c:
        owner_token = create_access_token({"sub": "usr-recalc-student", "email": "recalc@gov.in", "role": "STUDENT"})
        headers = {"Authorization": f"Bearer {owner_token}"}

        res1 = c.post("/api/student/me/roadmap/recalculate", headers=headers)
        assert res1.status_code == 200
        score1 = res1.json()["readiness_score"]
        py_step1 = next((s for s in res1.json()["roadmap"] if s["skill_id"] == "sk-001"), None)
        assert py_step1["status"] == "REVIEW"

        state["skills"] = [
            {"skill_id": "sk-001", "proficiency": "expert"},
            {"skill_id": "sk-002", "proficiency": "advanced"},
            {"skill_id": "sk-003", "proficiency": "advanced"},
        ]
        res2 = c.post("/api/student/me/roadmap/recalculate", headers=headers)
        assert res2.status_code == 200
        score2 = res2.json()["readiness_score"]
        assert score2 > score1
        py_step2 = next((s for s in res2.json()["roadmap"] if s["skill_id"] == "sk-001"), None)
        assert py_step2["status"] == "SKIP"


def test_demo_candidate_roadmap_without_auth():
    with TestClient(app) as c:
        res = c.get("/api/student/stu-001/roadmap")
        assert res.status_code == 200
        data = res.json()
        assert data["user_id"] == "stu-001"
        assert data["has_roadmap"] is True
        assert len(data["roadmap"]) >= 4
        assert "readiness_score" in data
        assert "summary" in data


def test_recalculate_roadmap_requires_auth_and_prevents_idor():
    save_user({"id": "usr-auth-recalc", "email": "authrecalc@gov.in", "role": "STUDENT", "full_name": "Auth Recalc"})
    save_user({"id": "usr-auth-other", "email": "otherrecalc@gov.in", "role": "STUDENT", "full_name": "Other Recalc"})
    save_user({"id": "usr-auth-admin", "email": "adminrecalc@gov.in", "role": "ADMIN", "full_name": "Admin Recalc"})

    with TestClient(app) as c:
        unauth = c.post("/api/student/usr-auth-recalc/roadmap/recalculate")
        assert unauth.status_code == 401

        other_token = create_access_token({"sub": "usr-auth-other", "email": "otherrecalc@gov.in", "role": "STUDENT"})
        forbidden = c.post(
            "/api/student/usr-auth-recalc/roadmap/recalculate",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert forbidden.status_code == 403

        admin_token = create_access_token({"sub": "usr-auth-admin", "email": "adminrecalc@gov.in", "role": "ADMIN"})
        admin_res = c.post(
            "/api/student/stu-001/roadmap/recalculate",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert admin_res.status_code == 200


def test_roadmap_computation_raises_on_repository_failure(monkeypatch):
    def failing_get_profile(uid):
        raise RuntimeError("Database connection refused")

    monkeypatch.setattr(supabase_repository, "get_student_profile", failing_get_profile)
    with pytest.raises(RuntimeError) as exc_info:
        compute_adaptive_roadmap("usr-real-student-123", is_demo=False)
    assert "Roadmap source data unavailable" in str(exc_info.value)
