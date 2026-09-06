import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories import supabase_repository
from app.repositories.supabase_repository import SupabaseRepositoryError
from app.services.career_recommendation_engine import compute_career_recommendations
from app.services.forecast_service import get_forecasts

client = TestClient(app)


def test_get_opportunity_preserves_stored_source(monkeypatch):
    stored_job = {
        "id": "job-real-stored-101",
        "title": "Machine Learning Engineer",
        "company": "Tech Corp",
        "district": "Pune",
        "industry": "IT",
        "source": "ADZUNA",
        "status": "active",
    }
    monkeypatch.setattr(supabase_repository, "get_job", lambda jid: stored_job if jid == "job-real-stored-101" else None)
    monkeypatch.setattr("app.routers.opportunities._get_skills_by_job", lambda **kwargs: {})

    response = client.get("/api/opportunities/job-real-stored-101")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "job-real-stored-101"
    assert data["source"] == "ADZUNA"


def test_get_opportunity_falls_back_to_unknown_when_source_absent(monkeypatch):
    stored_job = {
        "id": "job-real-stored-102",
        "title": "Data Analyst",
        "company": "Analytics Ltd",
        "district": "Mumbai",
        "industry": "IT",
        "source": None,
        "status": "active",
    }
    monkeypatch.setattr(supabase_repository, "get_job", lambda jid: stored_job if jid == "job-real-stored-102" else None)
    monkeypatch.setattr("app.routers.opportunities._get_skills_by_job", lambda **kwargs: {})

    response = client.get("/api/opportunities/job-real-stored-102")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "job-real-stored-102"
    assert data["source"] == "UNKNOWN"


def test_get_opportunity_real_mode_does_not_return_demo_fixtures(monkeypatch):
    monkeypatch.setattr(supabase_repository, "get_job", lambda jid: None)

    response = client.get("/api/opportunities/job-0001")
    assert response.status_code == 404
    assert response.json()["detail"] == "Opportunity not found"


def test_get_opportunity_demo_mode_returns_demo_job():
    response = client.get("/api/opportunities/job-0001?is_demo=true")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "job-0001"
    assert data["source"] == "DEMO_SYNTHETIC"


def test_career_recommendations_loads_persisted_course_skills(monkeypatch):
    student_profile = {
        "id": "usr-real-rec-001",
        "full_name": "Priya Sharma",
        "district": "Pune",
        "education": "Diploma",
        "skills": ["Python"],
        "target_career": "AI Engineer",
        "quiz_score_pct": 85,
        "source": "SUPABASE_AUTHORITATIVE",
        "is_demo": False,
    }
    monkeypatch.setattr(supabase_repository, "get_student_profile", lambda sid: student_profile)

    authoritative_courses = [
        {
            "id": "course-auth-901",
            "name": "Advanced Neural Networks Curriculum",
            "institute": "COEP Technological University",
            "district": "Pune",
            "category": "AI",
            "placement_rate": 92,
            "status": "active",
            "source": "INSTITUTE_SUBMITTED",
        }
    ]
    authoritative_course_skills = [
        {"course_id": "course-auth-901", "skill_id": "sk-gen-ai", "skill_name": "Generative AI"}
    ]
    authoritative_skills = [
        {"id": "sk-gen-ai", "name": "Generative AI"}
    ]

    monkeypatch.setattr(supabase_repository, "list_courses", lambda: authoritative_courses)
    monkeypatch.setattr(supabase_repository, "list_course_skills", lambda course_ids=None: authoritative_course_skills)
    monkeypatch.setattr(supabase_repository, "list_skills", lambda limit=10000: authoritative_skills)
    monkeypatch.setattr(supabase_repository, "list_employer_demands", lambda: [])
    monkeypatch.setattr(supabase_repository, "list_industry_signals", lambda: [])
    monkeypatch.setattr(supabase_repository, "list_skill_forecasts", lambda: [])

    result = compute_career_recommendations("usr-real-rec-001", is_demo=False)
    assert "top_recommendation" in result

    top_role = result["top_recommendation"]
    matched_training = top_role.get("matched_institute_training", [])
    matched_ids = [t.get("id") for t in matched_training]
    assert "course-auth-901" in matched_ids

    roadmap = result.get("personalized_roadmap", [])
    gen_ai_step = next((s for s in roadmap if "generative ai" in s.get("skill_name", "").lower()), None)
    assert gen_ai_step is not None
    training_options = gen_ai_step.get("matched_institute_training", [])
    option_ids = [opt.get("course_id") for opt in training_options]
    assert "course-auth-901" in option_ids


def test_career_recommendations_merges_existing_skills_with_persisted_course_skills(monkeypatch):
    student_profile = {
        "id": "usr-real-rec-002",
        "full_name": "Rohan Deshmukh",
        "district": "Pune",
        "education": "Degree",
        "skills": ["Python"],
        "target_career": "AI Engineer",
        "quiz_score_pct": 80,
        "source": "SUPABASE_AUTHORITATIVE",
        "is_demo": False,
    }
    monkeypatch.setattr(supabase_repository, "get_student_profile", lambda sid: student_profile)

    courses_with_partial_skills = [
        {
            "id": "course-auth-902",
            "name": "Machine Learning Foundations",
            "institute": "Pune Polytechnic",
            "district": "Pune",
            "skills": ["Existing Foundational Skill"],
            "status": "active",
            "source": "INSTITUTE_SUBMITTED",
        }
    ]
    course_skills_links = [
        {"course_id": "course-auth-902", "skill_id": "sk-rag", "skill_name": "RAG"}
    ]
    skills_map = [
        {"id": "sk-rag", "name": "RAG"}
    ]

    monkeypatch.setattr(supabase_repository, "list_courses", lambda: courses_with_partial_skills)
    monkeypatch.setattr(supabase_repository, "list_course_skills", lambda course_ids=None: course_skills_links)
    monkeypatch.setattr(supabase_repository, "list_skills", lambda limit=10000: skills_map)
    monkeypatch.setattr(supabase_repository, "list_employer_demands", lambda: [])
    monkeypatch.setattr(supabase_repository, "list_industry_signals", lambda: [])
    monkeypatch.setattr(supabase_repository, "list_skill_forecasts", lambda: [])

    result = compute_career_recommendations("usr-real-rec-002", is_demo=False)
    assert "top_recommendation" in result
    top_role = result["top_recommendation"]
    matched_training = top_role.get("matched_institute_training", [])
    matched_ids = [t.get("id") for t in matched_training]
    assert "course-auth-902" in matched_ids


def test_career_recommendations_demo_mode_isolated():
    result = compute_career_recommendations("stu-001", is_demo=True)
    assert "top_recommendation" in result
    top_role = result["top_recommendation"]
    matched_courses = top_role.get("matched_institute_training", [])
    for c in matched_courses:
        assert c.get("is_demo") is True or c.get("source") == "DEMO_SYNTHETIC"


def test_forecast_service_catches_supabase_repository_error_gracefully(monkeypatch):
    def failing_list_skill_forecasts(*args, **kwargs):
        raise SupabaseRepositoryError("Connection dropped")

    monkeypatch.setattr(supabase_repository, "list_skill_forecasts", failing_list_skill_forecasts)
    monkeypatch.setattr(supabase_repository, "list_skills", lambda *args, **kwargs: [])

    forecasts = get_forecasts(skill_id=None, is_demo=False)
    assert forecasts == []


def test_forecast_service_propagates_unexpected_programming_error(monkeypatch):
    def buggy_list_skill_forecasts(*args, **kwargs):
        raise TypeError("Unexpected argument type")

    monkeypatch.setattr(supabase_repository, "list_skill_forecasts", buggy_list_skill_forecasts)

    with pytest.raises(TypeError, match="Unexpected argument type"):
        get_forecasts(skill_id=None, is_demo=False)


def test_sync_engine_demo_mode_blocks_authoritative_writes(monkeypatch):
    from app.ingestion.sync_engine import SyncEngine

    supabase_writes = []

    monkeypatch.setattr("app.ingestion.sync_engine.is_explicit_demo_mode", lambda: True)
    monkeypatch.setattr("app.ingestion.sync_engine.is_supabase_connected", lambda: True)
    monkeypatch.setattr("app.ingestion.sync_engine.persist_schemes_to_supabase", lambda schemes: supabase_writes.append(("schemes", schemes)))
    monkeypatch.setattr("app.ingestion.sync_engine.persist_jobs_to_supabase", lambda jobs: supabase_writes.append(("jobs", jobs)))
    monkeypatch.setattr("app.repositories.supabase_repository.upsert_schemes", lambda schemes: supabase_writes.append(("upsert_schemes", schemes)))
    monkeypatch.setattr("app.repositories.supabase_repository.upsert_jobs", lambda jobs: supabase_writes.append(("upsert_jobs", jobs)))
    monkeypatch.setattr("app.repositories.supabase_repository.batch_create_job_skills", lambda links: supabase_writes.append(("batch_create_job_skills", links)))

    engine = SyncEngine()
    test_schemes = [{"source": "DEMO", "external_id": "sch-demo-1", "title": "Demo Scheme"}]
    test_jobs = [{"source": "DEMO", "external_id": "job-demo-1", "title": "Demo Job", "skill_ids": ["sk-1"]}]

    engine._upsert_schemes(test_schemes)
    engine._upsert_jobs(test_jobs)
    engine._upsert_job_skills(test_jobs)

    assert len(supabase_writes) == 0


def test_mcp_refresh_data_source_rejects_non_admin_caller():
    from app.mcp.tools import tool_refresh_data_source

    result = tool_refresh_data_source({"source": "data.gov.in", "role": "student"})
    assert result["status"] == "error"
    assert "Unauthorized" in result["error"]


def test_mcp_refresh_data_source_requires_admin_key_when_configured(monkeypatch):
    from app.config import settings
    from app.mcp.tools import tool_refresh_data_source

    async def fake_execute_sync(*, source):
        return {"status": "skipped", "records_fetched": 0}

    monkeypatch.setattr(settings, "admin_api_key", "secret-test-key-999")
    monkeypatch.setattr(
        "app.ingestion.scheduler.scheduler.execute_sync",
        fake_execute_sync,
    )

    result_unauthorized = tool_refresh_data_source({"source": "data.gov.in"})
    assert result_unauthorized["status"] == "error"
    assert "Unauthorized" in result_unauthorized["error"]

    result_wrong_key = tool_refresh_data_source({"source": "data.gov.in", "admin_key": "wrong-key"})
    assert result_wrong_key["status"] == "error"
    assert "Unauthorized" in result_wrong_key["error"]

    result_spoofed_role = tool_refresh_data_source({"source": "data.gov.in", "role": "ADMIN"})
    assert result_spoofed_role["status"] == "error"
    assert "Unauthorized" in result_spoofed_role["error"]

    result_authorized = tool_refresh_data_source({"source": "data.gov.in", "admin_key": "secret-test-key-999"})
    assert result_authorized["status"] in ("success", "skipped")
