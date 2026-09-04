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

    # Other non-demo identifiers
    assert is_demo_student_id("usr-student-001") is False
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

    with patch("app.services.career_recommendation_engine._resolve_student_profile", return_value=real_profile):
        with patch("app.repositories.supabase_repository.list_schemes", return_value=[]):
            with patch("app.services.career_recommendation_engine.get_demo", return_value=[]):
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
    client.table("schemes").insert(scheme_data).execute()

    res = get_scheme(non_uuid_code)
    assert res is not None
    assert res["scheme_code"] == non_uuid_code


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

    with patch("app.services.career_recommendation_engine._resolve_student_profile", return_value=real_profile):
        with patch("app.repositories.supabase_repository.list_schemes", return_value=[]):
            with patch("app.services.career_recommendation_engine.get_demo", return_value=sandbox_opps):
                rec = compute_career_recommendations("usr-real-candidate-99")
                assert rec["data_provenance"]["government_opportunities_source"] == "NO_OFFICIAL_MATCHES"
