"""Test suite for Phase 13: Database & Admin Data Management API."""
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.db import init_db
from app.config import settings

client = TestClient(app)
ADMIN_KEY = settings.admin_api_key or "demo-admin-key-2026"
HEADERS = {"X-Admin-Key": ADMIN_KEY}


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_admin_auth_failures():
    """Admin endpoints reject requests with missing or invalid X-Admin-Key header."""
    # 1. Missing header
    res_no_key = client.get("/api/admin/assessments")
    assert res_no_key.status_code == 401

    # 2. Invalid header
    res_bad_key = client.get("/api/admin/assessments", headers={"X-Admin-Key": "wrong-secret-key"})
    assert res_bad_key.status_code == 401

    # 3. Stats missing header
    res_stats_bad = client.get("/api/admin/assessments/stats/summary", headers={"X-Admin-Key": "invalid"})
    assert res_stats_bad.status_code == 401


def test_admin_list_assessments_success():
    """GET /api/admin/assessments returns paginated records with valid X-Admin-Key."""
    res = client.get("/api/admin/assessments", headers=HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "total" in data
    assert "assessments" in data
    assert len(data["assessments"]) > 0

    first = data["assessments"][0]
    assert "id" in first
    assert "name" in first
    assert "career_goal" in first
    assert "source" in first


def test_admin_filters_source_and_district():
    """Admin endpoints correctly filter by data source and district."""
    # Submit a distinct user assessment first
    client.post("/api/student/assessment", json={
        "name": "Pooja Patil",
        "education": "BE Civil Engineering",
        "district": "Solapur",
        "career_goal": "Cloud Architect",
        "interests": ["Cloud Computing"],
        "current_skills": [{"skill_name": "Cloud Computing", "proficiency": "intermediate"}],
        "quiz_answers": {"q1": "b", "q2": "c"},
    })

    # 1. Filter by source = USER_SUBMITTED
    res_user = client.get("/api/admin/assessments?source=USER_SUBMITTED", headers=HEADERS)
    assert res_user.status_code == 200
    for item in res_user.json()["assessments"]:
        assert item["source"] == "USER_SUBMITTED"

    # 2. Filter by source = DEMO_SYNTHETIC
    res_demo = client.get("/api/admin/assessments?source=DEMO_SYNTHETIC", headers=HEADERS)
    assert res_demo.status_code == 200
    for item in res_demo.json()["assessments"]:
        assert item["source"] == "DEMO_SYNTHETIC"

    # 3. Filter by district = Solapur
    res_dist = client.get("/api/admin/assessments?district=Solapur", headers=HEADERS)
    assert res_dist.status_code == 200
    assert any(a["name"] == "Pooja Patil" for a in res_dist.json()["assessments"])


def test_admin_search_and_career_goal_filter():
    """Admin search finds records by candidate name, course, or career goal."""
    res = client.get("/api/admin/assessments?search=Aarav", headers=HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert any("Aarav" in a["name"] for a in data["assessments"])

    # Search by career goal
    res_goal = client.get("/api/admin/assessments?career_goal=EV%20Technician", headers=HEADERS)
    assert res_goal.status_code == 200
    for a in res_goal.json()["assessments"]:
        assert "EV" in a["career_goal"] or "Technician" in a["career_goal"]


def test_admin_stats_summary():
    """GET /api/admin/assessments/stats/summary calculates accurate aggregates."""
    res = client.get("/api/admin/assessments/stats/summary", headers=HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "total_submissions" in data
    assert "user_submitted_count" in data
    assert "demo_synthetic_count" in data
    assert "avg_quiz_score" in data
    assert "avg_skill_match" in data
    assert "district_distribution" in data
    assert "career_goal_distribution" in data
    assert "top_missing_skills" in data
    assert "readiness_distribution" in data
    assert isinstance(data["district_distribution"], list)
    assert isinstance(data["top_missing_skills"], list)


def test_admin_detail_and_delete():
    """GET and DELETE /api/admin/assessments/{id} inspects and removes records."""
    # Create test record
    create_res = client.post("/api/student/assessment", json={
        "name": "Temporary Test Candidate",
        "education": "Diploma IT",
        "district": "Pune",
        "career_goal": "AI Engineer",
        "interests": ["AI / ML"],
        "current_skills": [{"skill_name": "Python", "proficiency": "beginner"}],
        "quiz_answers": {"q1": "a"},
    })
    test_id = create_res.json()["assessment"]["id"]

    # 1. Detail view
    detail_res = client.get(f"/api/admin/assessments/{test_id}", headers=HEADERS)
    assert detail_res.status_code == 200
    assert detail_res.json()["assessment"]["name"] == "Temporary Test Candidate"

    # 2. Delete
    del_res = client.delete(f"/api/admin/assessments/{test_id}", headers=HEADERS)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "success"

    # 3. Subsequent fetch returns 404
    after_del = client.get(f"/api/admin/assessments/{test_id}", headers=HEADERS)
    assert after_del.status_code == 404
