from unittest.mock import patch, MagicMock
import httpx
import pytest
from app.ingestion.datagov_connector import (
    DataGovConnector,
    RESOURCE_SCHOLARSHIP_ALLOCATION,
)
from app.ingestion.adzuna_connector import AdzunaConnector
from app.ingestion.industry_intelligence import (
    SAMPLE_VERIFIED_FEEDS,
    IndustryIntelligenceIngestor,
)
from app.ingestion.sync_engine import SyncEngine
from app.services.district_service import get_all_districts


def test_datagov_live_success_mocked():
    connector = DataGovConnector(api_key="genuine_test_key_12345")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "records": [
            {
                "id": "101",
                "state": "Maharashtra",
                "scheme_name": "Post-Matric Scholarship",
                "amount": "50000",
            }
        ]
    }

    with patch("httpx.get", return_value=mock_response):
        result = connector.fetch_resource(RESOURCE_SCHOLARSHIP_ALLOCATION, is_demo=False)

    assert result["status"] in ("SUCCESS", "ok")
    assert result["source_available"] is True
    assert result["error"] is None
    assert len(result["records"]) == 1
    assert result["records"][0]["is_sandbox"] is False


def test_datagov_auth_failure_no_demo_fallback():
    connector = DataGovConnector(api_key="invalid_test_key")
    mock_response = MagicMock()
    mock_response.status_code = 403

    with patch("httpx.get", return_value=mock_response):
        result = connector.fetch_resource(RESOURCE_SCHOLARSHIP_ALLOCATION, is_demo=False)

    assert result["status"] == "FAILED"
    assert result["source_available"] is False
    assert "authentication failed" in result["error"]
    assert result["records"] == []


def test_datagov_missing_api_key_no_demo_fallback():
    connector = DataGovConnector(api_key="")
    result = connector.fetch_resource(RESOURCE_SCHOLARSHIP_ALLOCATION, is_demo=False)

    assert result["status"] == "NOT_CONFIGURED"
    assert result["source_available"] is False
    assert "DATA_GOV_API_KEY is not configured" in result["error"]
    assert result["records"] == []


def test_datagov_timeout_no_demo_fallback():
    connector = DataGovConnector(api_key="valid_key")

    with patch("httpx.get", side_effect=httpx.TimeoutException("Connection timed out")):
        result = connector.fetch_resource(RESOURCE_SCHOLARSHIP_ALLOCATION, is_demo=False)

    assert result["status"] == "FAILED"
    assert result["source_available"] is False
    assert "Network issue" in result["error"]
    assert result["records"] == []


def test_datagov_zero_records_no_demo_fallback():
    connector = DataGovConnector(api_key="valid_key")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"records": []}

    with patch("httpx.get", return_value=mock_response):
        result = connector.fetch_resource(RESOURCE_SCHOLARSHIP_ALLOCATION, is_demo=False)

    assert result["status"] == "NO_DATA"
    assert result["source_available"] is True
    assert result["records"] == []


def test_datagov_explicit_demo_mode_allows_sandbox():
    connector = DataGovConnector(api_key="")
    result = connector.fetch_resource(RESOURCE_SCHOLARSHIP_ALLOCATION, is_demo=True)

    assert result["status"] in ("SUCCESS", "ok")
    assert result["source_available"] is True
    assert len(result["records"]) > 0
    assert result["records"][0].get("is_sandbox") is True


def test_adzuna_live_success_mocked():
    connector = AdzunaConnector(app_id="test_id", app_key="test_key")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {
                "id": "adz-12345",
                "title": "Robotics Engineer",
                "company": {"display_name": "Kirloskar Industries"},
                "location": {"display_name": "Pune, Maharashtra", "area": ["India", "Maharashtra", "Pune"]},
                "category": {"label": "Manufacturing"},
                "redirect_url": "https://www.adzuna.in/jobs/details/12345",
                "created": "2026-09-10T10:00:00Z",
            }
        ]
    }

    with patch("httpx.get", return_value=mock_response):
        results = connector.fetch_raw(is_demo=False)

    assert connector.last_status == "SUCCESS"
    assert connector.last_error is None
    assert len(results) == 1
    assert results[0]["is_snapshot"] is False


def test_adzuna_auth_failure_no_demo_fallback():
    connector = AdzunaConnector(app_id="invalid_id", app_key="invalid_key")
    mock_response = MagicMock()
    mock_response.status_code = 401

    with patch("httpx.get", return_value=mock_response):
        results = connector.fetch_raw(is_demo=False)

    assert connector.last_status == "FAILED"
    assert "authentication failed" in connector.last_error
    assert results == []


def test_adzuna_missing_credentials_no_demo_fallback():
    connector = AdzunaConnector(app_id="", app_key="")
    results = connector.fetch_raw(is_demo=False)

    assert connector.last_status == "NOT_CONFIGURED"
    assert "not configured" in connector.last_error
    assert results == []


def test_adzuna_timeout_no_demo_fallback():
    connector = AdzunaConnector(app_id="valid_id", app_key="valid_key")

    with patch("httpx.get", side_effect=httpx.TimeoutException("Adzuna timeout")):
        results = connector.fetch_raw(is_demo=False)

    assert connector.last_status == "FAILED"
    assert "Adzuna network issue" in connector.last_error
    assert results == []


def test_adzuna_explicit_demo_mode_allows_snapshot():
    connector = AdzunaConnector(app_id="", app_key="")
    results = connector.fetch_raw(is_demo=True)

    assert connector.last_status == "SUCCESS"
    assert len(results) > 0
    assert results[0].get("is_snapshot") is True


def test_industry_signals_synthetic_classified_as_demo():
    for item in SAMPLE_VERIFIED_FEEDS:
        assert item.get("is_demo") is True
        assert item.get("source_type") == "DEMO_SYNTHETIC"
        assert item.get("source_label") == "DEMO_SYNTHETIC"
        assert item.get("data_provenance") == "DEMO_SYNTHETIC"
        assert item.get("validation_status") in ("APPROVED", "DEMO")

    ingestor = IndustryIntelligenceIngestor()
    normalized, err = ingestor.validate_and_normalize(SAMPLE_VERIFIED_FEEDS[0])
    assert err is None
    assert normalized["is_demo"] is True
    assert normalized["data_provenance"] == "DEMO_SYNTHETIC"
    assert normalized["validation_status"] in ("APPROVED", "DEMO")


def test_signals_router_real_mode_no_synthetic_injection():
    import asyncio
    from app.routers.signals import legacy_list_signals

    with patch("app.routers.signals.list_industry_signals_repo", return_value=[]):
        signals = asyncio.run(legacy_list_signals(is_demo=False))

    assert signals == []


def test_district_service_real_mode_no_demo_fallback():
    with patch("app.repositories.supabase_repository.list_jobs", return_value=[]), \
         patch("app.repositories.supabase_repository.list_courses", return_value=[]):
        districts = get_all_districts(is_demo=False)

    assert districts == []


def test_sync_engine_status_matrix():
    dg_conn = DataGovConnector(api_key="")
    adz_conn = AdzunaConnector(app_id="", app_key="")
    engine = SyncEngine(datagov_connector=dg_conn, adzuna_connector=adz_conn)

    with patch("app.ingestion.sync_engine.is_explicit_demo_mode", return_value=False):
        log = engine.run_sync(source_name="all")

    assert log["status"] in ("failed", "partial")
    assert "data.gov.in" in log["sources_detail"]
    assert log["sources_detail"]["data.gov.in"]["status"] == "NOT_CONFIGURED"
    assert log["sources_detail"]["adzuna"]["status"] == "NOT_CONFIGURED"


def test_sync_status_endpoint_per_source():
    import asyncio
    from app.routers.sync import get_sync_status

    status_resp = asyncio.run(get_sync_status(is_demo=False))
    assert "sources" in status_resp
    assert "data.gov.in" in status_resp["sources"]
    assert "adzuna" in status_resp["sources"]
    assert "industry_signals" in status_resp["sources"]
    assert "skill_forecasts" in status_resp["sources"]
