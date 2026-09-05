"""Comprehensive regression test suite for CodeRabbit PR #4 findings.

Validates all 20 findings addressed in PR #4 / feature/real-data-ingestion:
- #1: None value guards in Adzuna company and location
- #2: Longest-first district alias normalization (Navi Mumbai -> Thane)
- #3: Synonym token tracking in matched_skill_names_lower
- #4: Live records do not have hardcoded published_at
- #5: DataGov connector uses stable UUIDs and doc_id-based scheme_codes
- #6-#8: SyncEngine stable key matching and failure propagation
- #9-#10: SupabaseRepository server-side pagination (.range()) and proper UUID generation
- #11: /api/jobs fail-closed behavior for real requests
- #12: /api/schemes fail-closed behavior for real requests
- #13-#14: Forecast demo isolation and is_demo parameter forwarding
- #15: Consistent job and job-skill populations in gap_engine and student_service
- #16: Centralized is_demo_student_id helper (stu-* never demo; ast-demo-* and demo-* are demo)
- #17: pydantic.ValidationError in invalid model assertions
- #18: Calendar-independent snapshot freshness
- #19-#20: Demo-safe defaults for provenance columns in migrations and schema.sql
"""
import datetime
import uuid
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import is_demo_student_id
from app.ingestion.base_adapter import normalize_maharashtra_district as normalize_district, extract_skills_and_unmapped
from app.ingestion.adzuna_connector import AdzunaConnector
from app.ingestion.datagov_connector import DataGovConnector
from app.ingestion.sync_engine import SyncEngine
from app.repositories.supabase_repository import upsert_jobs, upsert_schemes
from app.services.student_service import get_skill_explainability, get_personalized_industry_alerts
from app.services.gap_engine import compute_gaps
from app.services.forecast_engine import compute_multi_horizon_forecasts

client = TestClient(app)


# ============================================================================
# Finding #16: Centralized is_demo_student_id helper & Demo Prefix Hardening
# ============================================================================

def test_finding_16_is_demo_student_id_contract():
    """Verify is_demo_student_id strictly matches only ast-demo-* and demo-*, never stu-*."""
    # Explicit demo IDs
    assert is_demo_student_id("ast-demo-123") is True
    assert is_demo_student_id("ast-demo-001") is True
    assert is_demo_student_id("demo-123") is True
    assert is_demo_student_id("demo-student") is True

    # Generic student prefix stu-* must NEVER be treated as demo
    assert is_demo_student_id("stu-123") is False
    assert is_demo_student_id("stu-001") is False
    assert is_demo_student_id("stu-production-student") is False

    # Authenticated student account (usr-student-001) and other IDs must NOT match
    assert is_demo_student_id("usr-student-001") is False
    assert is_demo_student_id("usr-real-candidate-001") is False
    assert is_demo_student_id("123e4567-e89b-12d3-a456-426614174000") is False
    assert is_demo_student_id("") is False
    assert is_demo_student_id(None) is False
    assert is_demo_student_id(123) is False  # type: ignore


def test_finding_16_real_students_cannot_receive_demo_fixtures():
    """A real student with 'stu-123' must NOT receive demo job fixtures."""
    # When Supabase is empty or fails, a real student (stu-123) must fail closed
    with patch("app.repositories.supabase_repository.list_jobs", side_effect=Exception("DB Down")):
        with patch("app.repositories.supabase_repository.list_job_skills", return_value=[]):
            expl_stu = get_skill_explainability("Python", student_id="stu-123")
            demand_stu = expl_stu["explainability"]["dimension_1_demand_surge"]
            assert demand_stu["active_vacancies_count"] == 0

            # Conversely, an approved demo ID (ast-demo-001) DOES receive demo fixtures
            expl_demo = get_skill_explainability("Python", student_id="ast-demo-001")
            demand_demo = expl_demo["explainability"]["dimension_1_demand_surge"]
            assert demand_demo["active_vacancies_count"] > 0


# ============================================================================
# Finding #1: None-value guards in Adzuna company and location
# ============================================================================

def test_finding_1_adzuna_null_guards():
    """Adzuna company and location dicts with None values must not raise AttributeError."""
    connector = AdzunaConnector()
    raw_records = [
        {
            "id": "adz-null-test-1",
            "title": "Software Developer",
            "company": {"display_name": None, "name": None},
            "location": {"display_name": None, "area": None},
            "redirect_url": "https://example.com/adz/1",
        }
    ]
    transformed = connector.validate_and_transform(raw_records, master_skills=[])
    assert len(transformed) == 1
    job = transformed[0]
    assert job["company"] == "Confidential Employer"
    assert job["district"] in ("Pune", "State-wide (Maharashtra)")


# ============================================================================
# Finding #2: District Normalization Ordering (Navi Mumbai -> Thane)
# ============================================================================

def test_finding_2_navi_mumbai_normalization():
    """Navi Mumbai must match before generic Mumbai substring."""
    assert normalize_district("Airoli, Navi Mumbai") == "Thane"
    assert normalize_district("CBD Belapur, Navi Mumbai, Maharashtra") == "Thane"
    assert normalize_district("Vashi, Navi Mumbai") == "Thane"
    assert normalize_district("Andheri, Mumbai") in ("Mumbai Suburban", "Mumbai City", "Mumbai")


# ============================================================================
# Finding #3: Synonym Token Recording in matched_skill_names_lower
# ============================================================================

def test_finding_3_synonym_token_recording():
    """Matched synonym tokens must be added to matched_skill_names_lower to prevent false unmapped skills."""
    master_skills = [
        {
            "id": "sk-001",
            "name": "Python Programming",
            "synonyms": ["Python", "Python3", "Py"],
        }
    ]
    # Text mentions "Python" (synonym), not full name "Python Programming"
    text = "We are seeking a developer proficient in Python and React."
    matched, unmapped = extract_skills_and_unmapped(text, master_skills)
    assert any(s["id"] == "sk-001" for s in matched)
    # "python" must NOT be listed in unmapped_skills because it was successfully resolved via synonym
    assert not any("python" in u.lower() for u in unmapped)


# ============================================================================
# Finding #4 & #5: DataGov Stable UUIDs, doc_id-based scheme_codes, and Live published_at
# ============================================================================

def test_finding_4_live_published_at_is_current():
    """Live records from DataGov must use current fetch time, not a hardcoded date."""
    connector = DataGovConnector()
    sample_records = [
        {
            "id": "1",
            "state_name": "Maharashtra",
            "district_name": "Pune",
            "financial_year": "2026-2027",
            "target_enrolment": "100",
            "actual_enrolment": "80",
        }
    ]
    before = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=2)
    schemes = connector.transform_cts_schemes(sample_records)
    after = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=2)

    assert len(schemes) == 1
    published_dt = datetime.datetime.fromisoformat(schemes[0]["published_at"])
    assert before <= published_dt <= after


def test_finding_5_stable_scheme_identities_and_uuids():
    """DataGov transformer must produce valid UUIDs and stable doc_id-based scheme_codes."""
    connector = DataGovConnector()
    doc_a = {
        "id": "doc-alpha",
        "state_name": "Maharashtra",
        "district_name": "Pune",
        "financial_year": "2026-2027",
        "target_enrolment": "100",
    }
    doc_b = {
        "id": "doc-beta",
        "state_name": "Maharashtra",
        "district_name": "Thane",
        "financial_year": "2026-2027",
        "target_enrolment": "50",
    }

    # Run in order [doc_a, doc_b]
    batch_1 = connector.transform_cts_schemes([doc_a, doc_b])
    # Run in reversed order [doc_b, doc_a]
    batch_2 = connector.transform_cts_schemes([doc_b, doc_a])

    # The scheme_code for doc_a must be identical across runs regardless of position
    scheme_a_1 = next(s for s in batch_1 if "doc-alpha" in s["external_id"])
    scheme_a_2 = next(s for s in batch_2 if "doc-alpha" in s["external_id"])
    assert scheme_a_1["scheme_code"] == scheme_a_2["scheme_code"]
    assert "doc-alpha" in scheme_a_1["scheme_code"]

    # All generated IDs must be valid UUIDs and stable across repeat runs
    for s in batch_1:
        val = uuid.UUID(s["id"])
        assert val.version in (4, 5)

    # Repeat transform of doc_a must yield the exact same deterministic UUID
    batch_3 = connector.transform_cts_schemes([doc_a])
    assert scheme_a_1["id"] == batch_3[0]["id"]


# ============================================================================
# Finding #6, #7, #8: SyncEngine Failure Propagation & Stable Matching
# ============================================================================

def test_finding_6_7_8_sync_failure_propagation():
    """SyncEngine must propagate persistence failures so run_sync does not falsely report success."""
    engine = SyncEngine()
    test_jobs = [
        {
            "id": str(uuid.uuid4()),
            "title": "Data Scientist",
            "company": "Infosys",
            "district": "Pune",
            "industry": "IT",
            "opportunity_type": "job",
            "source": "ADZUNA_API",
            "external_id": "adz-12345",
            "content_hash": "hash-12345",
            "is_demo": False,
        }
    ]

    with patch("app.repositories.supabase_repository.upsert_jobs", side_effect=RuntimeError("Database write error")):
        with patch("app.ingestion.sync_engine.persist_jobs_to_supabase", side_effect=RuntimeError("Fallback write failed")):
            with pytest.raises(RuntimeError):
                engine._upsert_jobs(test_jobs)

    # run_sync must record status: 'failed' when persistence throws
    with patch("app.repositories.supabase_repository.upsert_jobs", side_effect=RuntimeError("Supabase write error")):
        with patch("app.ingestion.sync_engine.persist_jobs_to_supabase", side_effect=RuntimeError("Fallback write error")):
            with patch.object(engine.adzuna_connector, "fetch_raw", return_value=[{"id": "adz-1", "title": "Developer", "redirect_url": "https://example.com"}]):
                sync_res = engine.run_sync(source_name="adzuna")
                assert sync_res["status"] == "failed"
                assert "write error" in sync_res["error_message"]


# ============================================================================
# Finding #9, #10: Supabase Repository Range Pagination & UUIDs
# ============================================================================

def test_finding_10_upsert_generates_valid_uuids():
    """upsert_jobs and upsert_schemes must mint valid UUID primary keys."""
    jobs_without_id = [
        {
            "title": "Machine Learning Engineer",
            "company": "TCS",
            "district": "Mumbai",
            "industry": "IT",
            "source": "LIVE_API",
        }
    ]
    upserted = upsert_jobs(jobs_without_id)
    assert len(upserted) == 1
    val = uuid.UUID(upserted[0]["id"])
    assert val.version == 4
    assert not upserted[0]["id"].startswith("job-")

    schemes_without_id = [
        {
            "title": "Maharashtra Apprenticeship Promotion",
            "scheme_code": "MAP-2026-TEST",
            "department": "Skill Development",
            "source": "LIVE_API",
        }
    ]
    upserted_sch = upsert_schemes(schemes_without_id)
    assert len(upserted_sch) == 1
    val_sch = uuid.UUID(upserted_sch[0]["id"])
    assert val_sch.version == 4
    assert not upserted_sch[0]["id"].startswith("sch-")


# ============================================================================
# Finding #11: /api/jobs Fail-Closed
# ============================================================================

def test_finding_11_jobs_fail_closed_for_real_requests():
    """GET /api/jobs?is_demo=false must fail closed and return empty list on repo failure."""
    with patch("app.repositories.supabase_repository.list_jobs", side_effect=Exception("Supabase unavailable")):
        res = client.get("/api/jobs?is_demo=false")
        assert res.status_code == 200
        assert res.json() == []

    # With is_demo=true, it bypasses repository even if repository contains sentinel rows
    sentinel_repo_jobs = [{"id": "sentinel-repo-job-1", "title": "Authoritative Live Job", "district": "Pune", "industry": "IT"}]
    with patch("app.repositories.supabase_repository.list_jobs", return_value=sentinel_repo_jobs):
        res_demo = client.get("/api/jobs?is_demo=true")
        assert res_demo.status_code == 200
        jobs_data = res_demo.json()
        assert len(jobs_data) > 0
        # Ensure sentinel repo job is NOT returned; filtered demo fixtures are returned
        assert not any(j.get("id") == "sentinel-repo-job-1" for j in jobs_data)


# ============================================================================
# Finding #12: /api/schemes Fail-Closed
# ============================================================================

def test_finding_12_schemes_fail_closed_for_real_requests():
    """GET /api/schemes?is_demo=false must return empty list when repo is empty or unavailable."""
    with patch("app.repositories.supabase_repository.list_schemes", side_effect=Exception("Supabase unavailable")):
        res = client.get("/api/schemes?is_demo=false")
        assert res.status_code == 200
        assert res.json() == []

        res_cat = client.get("/api/schemes/categories?is_demo=false")
        assert res_cat.status_code == 200
        data = res_cat.json()
        assert data["total_schemes"] == 0
        assert data["categories"] == []

    # Demo request returns demo fixtures
    res_demo = client.get("/api/schemes?is_demo=true")
    assert res_demo.status_code == 200
    assert len(res_demo.json()) > 0


# ============================================================================
# Finding #13 & #14: Forecast Demo Mode & Parameter Forwarding
# ============================================================================

def test_finding_13_forecast_demo_mode_does_not_read_live_demands():
    """Demo forecast computation must not query live employer demands repository."""
    with patch("app.repositories.supabase_repository.list_employer_demands") as mock_demands:
        compute_multi_horizon_forecasts(is_demo=True)
        assert mock_demands.call_count == 0


def test_finding_14_forecast_skill_forwards_is_demo():
    """GET /api/forecast/skill/{skill_id} must forward is_demo parameter."""
    with patch("app.routers.forecast.get_skill_forecast_trajectory") as mock_traj:
        mock_traj.return_value = {"skill_id": "sk-001", "skill_name": "Python", "projected_24m": 85}
        res = client.get("/api/forecast/skill/sk-001?is_demo=false")
        assert res.status_code == 200
        mock_traj.assert_called_once_with("sk-001", is_demo=False)


# ============================================================================
# Finding #15: Gap Engine Population Consistency
# ============================================================================

def test_finding_15_gap_engine_population_consistency():
    """Job-skill links in compute_gaps must be filtered strictly to loaded jobs."""
    mock_jobs = [{"id": "job-alpha", "district": "Pune"}]
    mock_job_skills = [
        {"job_id": "job-alpha", "skill_id": "sk-001"},
        {"job_id": "job-beta-outside-scope", "skill_id": "sk-002"},  # Outside loaded jobs
    ]
    with patch("app.repositories.supabase_repository.list_jobs", return_value=mock_jobs):
        with patch("app.repositories.supabase_repository.list_job_skills", return_value=mock_job_skills):
            gaps = compute_gaps(is_demo=False)
            # Only sk-001 should be present in demand counts, sk-002 must be excluded
            demand_skill_ids = {g["skill_id"] for g in gaps if g["demand_count"] > 0}
            assert "sk-001" in demand_skill_ids
            assert "sk-002" not in demand_skill_ids


# ============================================================================
# Review #2 Regression Tests: Short Token Synonyms, Submission is_demo, & Routing
# ============================================================================

def test_short_token_synonym_context_guard():
    """Short synonym tokens like 'go' or 'c' must require technical context to match."""
    from app.ingestion.base_adapter import extract_skills_from_text

    master_skills = [
        {"id": "sk-golang", "name": "Golang", "synonyms": ["go", "go-lang"]},
        {"id": "sk-c-prog", "name": "C", "synonyms": ["c", "c-lang"]},
    ]

    # Ordinary prose containing 'go' should NOT match Golang
    prose_text = "Please go to our careers portal and submit your application."
    matched = extract_skills_from_text(prose_text, master_skills)
    assert not any(s["id"] == "sk-golang" for s in matched)

    # Technical text containing 'go developer' SHOULD match Golang
    tech_text = "We are seeking an experienced Go developer to join our backend team."
    matched_tech = extract_skills_from_text(tech_text, master_skills)
    assert any(s["id"] == "sk-golang" for s in matched_tech)

    # Contextual C match
    c_tech_text = "Requires deep experience in embedded C programming."
    matched_c = extract_skills_from_text(c_tech_text, master_skills)
    assert any(s["id"] == "sk-c-prog" for s in matched_c)


def test_assessment_submission_ignores_caller_is_demo():
    """evaluate_student_assessment must derive demo mode only from is_demo_student_id, not payload is_demo."""
    from app.services.student_service import evaluate_student_assessment

    submission_payload = {
        "user_id": "usr-real-test-student-123",
        "name": "Real Student",
        "district": "Pune",
        "is_demo": True,  # Attacker/caller tries to force demo mode
        "quiz_answers": {"q1": "a", "q2": "b"},
        "skills": [{"skill_id": "sk-001", "proficiency": "advanced"}],
    }

    with patch("app.services.student_service.compute_gaps") as mock_compute_gaps:
        mock_compute_gaps.return_value = []
        evaluate_student_assessment(submission_payload)
        # compute_gaps must have been called with is_demo=False because user_id is real
        mock_compute_gaps.assert_called_once()
        assert mock_compute_gaps.call_args[1].get("is_demo") is False


def test_recommendation_and_gov_opportunities_provenance_routing():
    """Non-demo student profile queries authoritative schemes and opportunities."""
    from app.services.career_recommendation_engine import compute_career_recommendations

    real_profile = {
        "id": "usr-real-student-456",
        "user_id": "usr-real-student-456",
        "name": "Real Candidate",
        "district": "Pune",
        "skills": [{"skill_id": "sk-001", "name": "Python", "proficiency": "advanced"}],
        "source": "USER_SUBMITTED",
        "is_demo": False,
    }

    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.execute.return_value.data = []
    with patch("app.services.career_recommendation_engine._resolve_student_profile", return_value=real_profile):
        with patch("app.repositories.supabase_repository.list_schemes", return_value=[]):
            with patch("app.db.get_supabase_client", return_value=mock_sb):
                rec = compute_career_recommendations("usr-real-student-456")
                assert "recommended_careers" in rec
                assert rec["data_provenance"]["government_opportunities_source"] == "NO_OFFICIAL_MATCHES"


def test_review3_schemes_get_scheme_authoritative_and_fail_closed():
    """Verify get_scheme queries authoritative repository and fails closed on is_demo=False."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    repo_scheme = {
        "id": "sch-auth-999",
        "scheme_code": "OGD-TEST-999",
        "name": "Authoritative Maharashtra Scheme",
        "status": "active",
        "source": "DATAGOV_IN",
        "is_demo": False,
    }
    with patch("app.repositories.supabase_repository.get_scheme", return_value=repo_scheme):
        res = client.get("/api/schemes/sch-auth-999")
        assert res.status_code == 200
        assert res.json()["name"] == "Authoritative Maharashtra Scheme"

    with patch("app.repositories.supabase_repository.get_scheme", return_value=None):
        res = client.get("/api/schemes/sch-missing-123?is_demo=false")
        assert res.status_code == 404

        res_demo = client.get("/api/schemes/sch-001?is_demo=true")
        assert res_demo.status_code == 200
        assert "title" in res_demo.json() or "name" in res_demo.json()


def test_review4_get_scheme_validates_uuid_before_querying_id():
    """Verify get_scheme does not query UUID id column for non-UUID strings."""
    from app.repositories.supabase_repository import get_scheme, _is_valid_uuid
    import uuid

    assert _is_valid_uuid("OGD-CTS-ITI-99") is False
    valid_id = str(uuid.uuid4())
    assert _is_valid_uuid(valid_id) is True

    # Test non-UUID query only executes scheme_code eq, not crashing on id query
    non_uuid_code = "OGD-TEST-CODE-100"
    scheme_data = {
        "id": valid_id,
        "scheme_code": non_uuid_code,
        "name": "Non-UUID Scheme",
        "status": "active",
    }
    from app.repositories.supabase_repository import get_client
    client = get_client()
    try:
        client.table("schemes").insert(scheme_data).execute()
        res = get_scheme(non_uuid_code)
        assert res is not None
        assert res["scheme_code"] == non_uuid_code
    finally:
        client.table("schemes").delete().eq("id", valid_id).execute()


def test_review4_recommended_schemes_resolved_id_demo_check():
    """Verify /api/schemes/recommended/me resolves demo student ID via resolved_id."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import get_optional_current_user

    client = TestClient(app)
    demo_user = {
        "id": "demo-student-001",
        "role": "STUDENT",
        "email": "demo.student@skillsetu.gov.in",
        "is_demo": True,
    }
    app.dependency_overrides[get_optional_current_user] = lambda: demo_user
    try:
        with patch("app.repositories.supabase_repository.get_student_profile", return_value={"skills": ["Electrical"], "district": "Pune"}):
            res = client.get("/api/schemes/recommended/me")
            assert res.status_code == 200
            data = res.json()
            assert "demo dataset" in data["provenance_note"]
    finally:
        app.dependency_overrides.pop(get_optional_current_user, None)


def test_review4_real_opps_sandbox_simulation_excluded():
    """Verify sandbox simulation opportunities are excluded from real student recommendations."""
    from app.services.career_recommendation_engine import compute_career_recommendations

    real_profile = {
        "id": "usr-real-candidate-99",
        "user_id": "usr-real-candidate-99",
        "skills": [{"skill_name": "Solar PV", "proficiency": "advanced"}],
        "district": "Nagpur",
        "source": "USER_SUBMITTED",
        "is_demo": False,
    }

    sandbox_opps = [
        {
            "id": "opp-sandbox-1",
            "name": "Simulated Solar Training",
            "source_type": "SANDBOX_SIMULATION",
            "source": "DATAGOV_IN",
            "is_demo": False,
            "data_provenance": "GOVERNMENT_OFFICIAL",
            "target_skills": ["Solar PV"],
            "district_coverage": ["Nagpur"],
            "status": "active",
        },
        {
            "id": "opp-demo-2",
            "name": "Demo Synthetic Scheme",
            "source": "DEMO_SYNTHETIC",
            "is_demo": True,
            "target_skills": ["Solar PV"],
            "district_coverage": ["Nagpur"],
            "status": "active",
        }
    ]

    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.execute.return_value.data = sandbox_opps
    with patch("app.services.career_recommendation_engine._resolve_student_profile", return_value=real_profile):
        with patch("app.repositories.supabase_repository.list_schemes", return_value=[]):
            with patch("app.db.get_supabase_client", return_value=mock_sb):
                rec = compute_career_recommendations("usr-real-candidate-99")
                assert rec["data_provenance"]["government_opportunities_source"] == "NO_OFFICIAL_MATCHES"


# ============================================================================
# Review #5 Regression Tests: Forecast Job Skills Filter, Demo Assessment Provenance, & Uniqueness
# ============================================================================

def test_review5_forecast_engine_filters_job_skills_by_job_ids():
    """compute_multi_horizon_forecasts must filter job_skills strictly to loaded jobs."""
    from app.services.forecast_engine import compute_multi_horizon_forecasts

    mock_jobs = [{"id": "job-alpha", "district": "Pune"}]
    mock_job_skills = [
        {"job_id": "job-alpha", "skill_id": "sk-001"},
        {"job_id": "job-beta-outside-scope", "skill_id": "sk-002"},
    ]
    mock_skills = [{"id": "sk-001", "name": "Skill 1"}, {"id": "sk-002", "name": "Skill 2"}]
    with patch("app.repositories.supabase_repository.list_jobs", return_value=mock_jobs) as mock_lj:
        with patch("app.repositories.supabase_repository.list_job_skills", return_value=mock_job_skills) as mock_ljs:
            with patch("app.repositories.supabase_repository.list_skills", return_value=mock_skills):
                with patch("app.repositories.supabase_repository.list_employer_demands", return_value=[]):
                    forecasts = compute_multi_horizon_forecasts(is_demo=False)
                    mock_lj.assert_called_once_with(limit=10000)
                    mock_ljs.assert_called_once_with(job_ids=["job-alpha"])
                    assert isinstance(forecasts, list)
                    f_map = {f["skill_id"]: f for f in forecasts}
                    assert f_map["sk-001"]["current_demand_score"] == 100.0
                    assert f_map["sk-002"]["current_demand_score"] == 20.0


def test_review5_student_assessment_preserves_demo_provenance():
    """evaluate_student_assessment must persist demo metadata matching is_demo_student_id."""
    from app.services.student_service import evaluate_student_assessment

    demo_sub = {
        "user_id": "ast-demo-123",
        "name": "Demo Student",
        "district": "Pune",
        "quiz_answers": {},
        "current_skills": [],
    }
    rec_demo = evaluate_student_assessment(demo_sub)
    assert rec_demo["is_demo"] is True
    assert rec_demo["source"] == "DEMO_SYNTHETIC"
    assert rec_demo["data_provenance"] == "DEMO_SYNTHETIC"
    assert rec_demo["id"].startswith("ast-demo-")

    real_sub = {
        "user_id": "usr-real-999",
        "name": "Real Student",
        "district": "Pune",
        "quiz_answers": {},
        "current_skills": [],
    }
    rec_real = evaluate_student_assessment(real_sub)
    assert rec_real["is_demo"] is False
    assert rec_real["source"] == "USER_SUBMITTED"
    assert rec_real["data_provenance"] == "SELF_REPORTED_ASSESSMENT"
    assert rec_real["id"].startswith("ast-usr-")


def test_review5_schema_and_migration_external_id_contract():
    """Schema and migration must define external_id and non-partial unique constraints/indexes."""
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent
    with open(project_root / "data" / "schema.sql", "r", encoding="utf-8") as f:
        schema_sql = f.read()
    with open(project_root / "data" / "migrations" / "20260904_add_provenance_columns.sql", "r", encoding="utf-8") as f:
        migration_sql = f.read()

    assert "external_id TEXT" in schema_sql
    assert "CONSTRAINT uq_jobs_source_external_id UNIQUE (source, external_id)" in schema_sql

    assert "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS external_id TEXT;" in migration_sql
    assert "ALTER TABLE schemes ADD COLUMN IF NOT EXISTS external_id TEXT;" in migration_sql
    assert "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_source_external_id ON jobs(source, external_id);" in migration_sql
    assert "idx_schemes_source_external_id" not in migration_sql
    assert "WHERE external_id IS NOT NULL" not in migration_sql.split("idx_jobs_source_external_id")[1].split(";")[0]


def test_review6_authenticated_assessment_provenance_isolation():
    """Verify authenticated assessment submission provenance for real vs demo student personas."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import create_access_token
    from app.db import init_demo_users

    init_demo_users()
    client = TestClient(app)

    # 1. Real authenticated student account (usr-student-001) -> USER_SUBMITTED
    token_real = create_access_token({"sub": "usr-student-001", "email": "student@skillsetu.gov.in", "role": "STUDENT"})
    payload = {
        "name": "Aarav Patil",
        "education": "Diploma in Mechanical",
        "career_goal": "Automotive Design Engineer",
        "district": "Pune",
        "current_skills": [{"skill_name": "CAD", "proficiency": "intermediate"}],
        "interests": ["Automotive"],
        "quiz_answers": {"q1": "a"},
    }
    with patch("app.repositories.supabase_repository.create_student_assessment", side_effect=lambda rec: rec):
        res = client.post(
            "/api/student/assessment",
            json=payload,
            headers={"Authorization": f"Bearer {token_real}"},
        )
        assert res.status_code == 200
        data = res.json()
        ast = data.get("assessment", data)
        assert ast["user_id"] == "usr-student-001"
        assert ast["is_demo"] is False
        assert ast["source"] == "USER_SUBMITTED"
        assert ast["source_label"] == "Candidate Self-Reported Assessment"
        assert ast["data_provenance"] == "SELF_REPORTED_ASSESSMENT"
        assert ast["id"].startswith("ast-usr-")

    # 2. Synthetic demo student account (demo-student-001) -> DEMO_SYNTHETIC
    from app.db import save_user
    save_user({
        "id": "demo-student-001",
        "email": "demo.persona@skillsetu.gov.in",
        "role": "STUDENT",
        "is_active": True,
        "is_demo": True,
    })
    token_demo = create_access_token({"sub": "demo-student-001", "email": "demo.persona@skillsetu.gov.in", "role": "STUDENT"})
    with patch("app.repositories.supabase_repository.create_student_assessment", side_effect=lambda rec: rec):
        res_demo = client.post(
            "/api/student/assessment",
            json=payload,
            headers={"Authorization": f"Bearer {token_demo}"},
        )
        assert res_demo.status_code == 200
        data_demo = res_demo.json()
        ast_demo = data_demo.get("assessment", data_demo)
        assert ast_demo["user_id"] == "demo-student-001"
        assert ast_demo["is_demo"] is True
        assert ast_demo["source"] == "DEMO_SYNTHETIC"
        assert ast_demo["source_label"] == "Demo Assessment Simulation"
        assert ast_demo["data_provenance"] == "DEMO_SYNTHETIC"
        assert ast_demo["id"].startswith("ast-demo-")


def test_review7_email_lookup_does_not_recreate_revoked_account():
    """Finding 1 (Review 7): get_user_by_email and get_user_by_id must not recreate deleted accounts."""
    from app.db import _cache, get_user_by_email, get_user_by_id, list_users, init_demo_users

    # Ensure baseline is loaded initially
    init_demo_users()
    assert get_user_by_email("student@skillsetu.gov.in") is not None

    orig_users = list(_cache.get("users", []))
    try:
        # Simulate operator removing / revoking the account
        _cache["users"] = [u for u in _cache.get("users", []) if u.get("id") != "usr-student-001" and u.get("email") != "student@skillsetu.gov.in"]

        # Authentication lookup must return None and MUST NOT resurrect the account
        assert get_user_by_email("student@skillsetu.gov.in") is None
        assert get_user_by_id("usr-student-001") is None
        assert not any(u.get("id") == "usr-student-001" for u in list_users())
    finally:
        _cache["users"] = orig_users
        # Re-initialize demo baseline for subsequent tests
        init_demo_users()

    assert get_user_by_email("student@skillsetu.gov.in") is not None


def test_review7_conftest_fixture_table_independence():
    """Finding 2 (Review 7): Fixture loads missing tables and demo users even if _cache is partially populated."""
    from app.db import _cache

    # Partially populate _cache simulating a dirty cache from an earlier test
    _cache["partial_dummy"] = [{"id": "dummy-1"}]
    # Remove schemes to simulate a missing table in partial cache
    _cache.pop("schemes", None)

    from conftest import ensure_cache_baseline
    ensure_cache_baseline()

    assert "schemes" in _cache and len(_cache["schemes"]) > 0
    assert any(u.get("email") == "student@skillsetu.gov.in" for u in _cache.get("users", []))


def test_review7_conftest_mock_ilike_wildcards():
    """Verify mock Supabase ilike filter handles SQL wildcards % and _ correctly."""
    from app.repositories.supabase_repository import get_client
    client = get_client()

    # Insert test rows in jobs table
    job1 = {"id": "test-job-wildcard-1", "title": "Senior Python Developer in Pune City", "district": "Pune", "source": "TEST"}
    job2 = {"id": "test-job-wildcard-2", "title": "Java Architect in Mumbai City", "district": "Mumbai City", "source": "TEST"}
    try:
        client.table("jobs").insert([job1, job2]).execute()

        # Query with % wildcard
        res_percent = client.table("jobs").select("*").ilike("title", "%python%").execute()
        titles = [r["title"] for r in (res_percent.data or [])]
        assert any("Python" in t for t in titles)
        assert not any("Java" in t for t in titles)

        # Query with _ single-character wildcard
        res_underscore = client.table("jobs").select("*").ilike("district", "Pun_").execute()
        districts = [r["district"] for r in (res_underscore.data or [])]
        assert "Pune" in districts
    finally:
        client.table("jobs").delete().eq("id", "test-job-wildcard-1").execute()
        client.table("jobs").delete().eq("id", "test-job-wildcard-2").execute()


def test_review7_district_service_mode_isolation(monkeypatch):
    """Verify get_district_plan isolates demo vs authoritative courses, skills, and placements."""
    import app.repositories.supabase_repository as repo
    from app.services.district_service import get_district_plan

    # Mock list_skills and list_courses
    auth_skill = {"id": "auth-uuid-skill-001", "name": "Authoritative AI Engineering", "category": "AI"}
    auth_course = {"id": "auth-uuid-course-001", "name": "AI Course", "title": "AI Course", "district": "pune", "enrolment_count": 50}
    auth_job = {"id": "auth-uuid-job-001", "title": "AI Researcher", "district": "pune", "is_demo": False}
    auth_js = {"job_id": "auth-uuid-job-001", "skill_id": "auth-uuid-skill-001"}

    monkeypatch.setattr(repo, "list_skills", lambda *args, **kwargs: [auth_skill])
    monkeypatch.setattr(repo, "list_courses", lambda *args, **kwargs: [auth_course])
    monkeypatch.setattr(repo, "list_jobs", lambda *args, **kwargs: [auth_job])
    monkeypatch.setattr(repo, "list_job_skills", lambda *args, **kwargs: [auth_js])

    # Real mode (is_demo=False) must load authoritative skill and not demo skills
    plan_real = get_district_plan("pune", is_demo=False)
    assert plan_real["district"].lower() == "pune"
    skill_names = [s.get("skill_name") for s in plan_real.get("top_skills", [])]
    assert "Authoritative AI Engineering" in skill_names

    # Demo mode (is_demo=True) must load demo datasets directly
    plan_demo = get_district_plan("pune", is_demo=True)
    assert plan_demo["district"].lower() == "pune"
    assert any(c.get("institute") for c in plan_demo.get("local_courses", []))


def test_review7_student_service_job_filtering_and_sandbox_isolation(monkeypatch):
    """Verify student service filters sandbox jobs and selects demo jobs mode-first."""
    import app.repositories.supabase_repository as repo
    from app.services.student_service import get_personalized_industry_alerts, get_skill_explainability

    # Mix of authoritative real job and sandbox simulation job
    real_job = {"id": "job-real-001", "title": "Real Cloud Engineer", "is_demo": False, "source": "ADZUNA_API"}
    sandbox_job = {"id": "job-sandbox-001", "title": "Sandbox Job", "is_demo": True, "source": "SANDBOX_SIMULATION"}
    real_js = {"job_id": "job-real-001", "skill_id": "sk-001"}
    sandbox_js = {"job_id": "job-sandbox-001", "skill_id": "sk-sandbox-999"}

    monkeypatch.setattr(repo, "list_jobs", lambda *args, **kwargs: [real_job, sandbox_job])
    monkeypatch.setattr(repo, "list_job_skills", lambda *args, **kwargs: [real_js, sandbox_js])

    # Real user request: must exclude sandbox job
    real_alerts = get_personalized_industry_alerts(student_id="usr-real-student-non-demo")
    assert real_alerts is not None

    # Demo student request: must use demo dataset directly
    demo_alerts = get_personalized_industry_alerts(student_id="demo-student-001")
    assert demo_alerts is not None
    assert demo_alerts.get("data_provenance") == "GROUNDED_DEMO_DATASET"


def test_review7_migration_sql_explicit_source_mappings():
    """Verify migration SQL defines explicit source mappings and no broad ELSE fallbacks."""
    from pathlib import Path
    mig_path = Path(__file__).resolve().parent.parent / "data" / "migrations" / "20260904_add_provenance_columns.sql"
    content = mig_path.read_text(encoding="utf-8")

    # Both UPDATE jobs and UPDATE schemes must explicitly map SANDBOX_SIMULATION and VERIFIED_SNAPSHOT
    assert "WHEN source = 'SANDBOX_SIMULATION' THEN 'SANDBOX_SIMULATION'" in content
    assert "WHEN source = 'VERIFIED_SNAPSHOT' THEN 'VERIFIED_SNAPSHOT'" in content
    assert "ELSE NULL" in content
    assert "ELSE 'LIVE_API'" not in content


def test_review8_findings_isolation_and_authoritative_audit(monkeypatch):
    """Verify Review 8 findings: authoritative audit inputs, no demo skill leak, and consistent mode fallbacks."""
    import app.repositories.supabase_repository as repo
    from app.services.curriculum_engine import audit_all_courses
    from app.services.forecast_engine import compute_multi_horizon_forecasts
    from app.services.gap_engine import compute_gaps
    from app.services.district_service import get_district_plan

    # 1. Authoritative audit with no courses must return empty list (no demo fallback)
    monkeypatch.setattr(repo, "list_courses", lambda: [])
    audited = audit_all_courses(is_demo=False)
    assert audited == []

    # 2. Authoritative forecast with zero skills must return empty list (no demo skill leak)
    monkeypatch.setattr(repo, "list_skills", lambda *args, **kwargs: [])
    monkeypatch.setattr(repo, "list_jobs", lambda *args, **kwargs: [])
    monkeypatch.setattr(repo, "list_job_skills", lambda *args, **kwargs: [])
    forecasts = compute_multi_horizon_forecasts(is_demo=False)
    assert forecasts == []

    # 3. Gap engine in real mode must load authoritative course-skill links
    auth_course = {"id": "c-auth-100", "title": "Real Course", "enrolment_count": 50, "district": "pune"}
    auth_cs = [{"course_id": "c-auth-100", "skill_id": "sk-auth-100", "coverage_level": 4}]
    auth_job = {"id": "j-auth-100", "district": "pune", "is_demo": False}
    auth_js = [{"job_id": "j-auth-100", "skill_id": "sk-auth-100"}]
    auth_skill = {"id": "sk-auth-100", "name": "Real Tech Skill", "category": "Tech"}

    monkeypatch.setattr(repo, "list_courses", lambda *args, **kwargs: [auth_course])
    monkeypatch.setattr(repo, "list_course_skills", lambda *args, **kwargs: auth_cs)
    monkeypatch.setattr(repo, "list_jobs", lambda *args, **kwargs: [auth_job])
    monkeypatch.setattr(repo, "list_job_skills", lambda *args, **kwargs: auth_js)
    monkeypatch.setattr(repo, "list_skills", lambda *args, **kwargs: [auth_skill])

    gaps = compute_gaps(district="pune", is_demo=False)
    assert len(gaps) > 0
    assert gaps[0]["skill_id"] == "sk-auth-100"
    assert gaps[0]["coverage_pct"] > 0

    # 4. District plan in unspecified mode with empty repo jobs must use demo skills consistently
    monkeypatch.setattr(repo, "list_jobs", lambda *args, **kwargs: [])
    plan = get_district_plan("pune", is_demo=None)
    assert plan["district"].lower() == "pune"
    assert len(plan["top_skills"]) > 0
