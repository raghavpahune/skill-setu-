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


def test_sync_status_latest_failed_reports_failed():
    import asyncio
    from app.routers.sync import get_sync_status

    failed_log = {
        "id": "log-fail-1",
        "source_name": "data.gov.in",
        "job_type": "scheduled_sync",
        "status": "failed",
        "records_fetched": 0,
        "records_added": 0,
        "records_updated": 0,
        "records_skipped": 0,
        "error_message": "data.gov.in: FAILED - 403 Forbidden: authentication failed",
        "started_at": "2026-09-12T00:00:00Z",
        "completed_at": "2026-09-12T00:00:01Z",
        "sources_detail": {
            "data.gov.in": {
                "status": "FAILED",
                "error": "403 Forbidden: authentication failed",
                "records_fetched": 0,
                "records_added": 0,
                "records_updated": 0,
                "records_skipped": 0,
            }
        },
    }

    with patch("app.ingestion.datagov_connector.DataGovConnector.has_api_key", True), \
         patch("app.repositories.supabase_repository.list_sync_logs", return_value=[failed_log]), \
         patch("app.db._cache", {"sync_logs": [failed_log]}):
        res = asyncio.run(get_sync_status(is_demo=False))

    assert res["status"] == "failed"
    assert res["sources"]["data.gov.in"]["status"] == "FAILED"
    assert res["sources"]["data.gov.in"]["configured"] is True
    assert "403 Forbidden" in res["sources"]["data.gov.in"]["error"]
    assert res["sources"]["data.gov.in"]["records_fetched"] == 0
    assert res["last_sync"]["id"] == "log-fail-1"


def test_sync_status_configured_credentials_zero_records_no_data():
    import asyncio
    from app.routers.sync import get_sync_status

    nodata_log = {
        "id": "log-nodata-1",
        "source_name": "data.gov.in",
        "job_type": "scheduled_sync",
        "status": "success",
        "records_fetched": 0,
        "records_added": 0,
        "records_updated": 0,
        "records_skipped": 0,
        "error_message": None,
        "started_at": "2026-09-12T00:00:00Z",
        "completed_at": "2026-09-12T00:00:01Z",
        "sources_detail": {
            "data.gov.in": {
                "status": "NO_DATA",
                "error": None,
                "records_fetched": 0,
                "records_added": 0,
                "records_updated": 0,
                "records_skipped": 0,
            }
        },
    }

    with patch("app.ingestion.datagov_connector.DataGovConnector.has_api_key", True), \
         patch("app.repositories.supabase_repository.list_sync_logs", return_value=[nodata_log]), \
         patch("app.db._cache", {"sync_logs": [nodata_log]}):
        res = asyncio.run(get_sync_status(is_demo=False))

    assert res["sources"]["data.gov.in"]["status"] == "NO_DATA"
    assert res["sources"]["data.gov.in"]["error"] is None
    assert res["sources"]["data.gov.in"]["records_fetched"] == 0
    assert res["status"] == "degraded"


def test_sync_status_historical_success_not_masking_current_failure():
    import asyncio
    from app.routers.sync import get_sync_status

    recent_fail = {
        "id": "log-recent-fail",
        "source_name": "data.gov.in",
        "status": "failed",
        "records_fetched": 0,
        "error_message": "data.gov.in: FAILED - Connection timed out",
        "started_at": "2026-09-12T02:00:00Z",
        "completed_at": "2026-09-12T02:00:02Z",
        "sources_detail": {
            "data.gov.in": {
                "status": "FAILED",
                "error": "Connection timed out",
                "records_fetched": 0,
            }
        },
    }
    old_success = {
        "id": "log-old-success",
        "source_name": "data.gov.in",
        "status": "success",
        "records_fetched": 50,
        "records_added": 50,
        "records_updated": 0,
        "records_skipped": 0,
        "error_message": None,
        "started_at": "2026-09-11T02:00:00Z",
        "completed_at": "2026-09-11T02:00:05Z",
        "sources_detail": {
            "data.gov.in": {
                "status": "SUCCESS",
                "error": None,
                "records_fetched": 50,
                "records_added": 50,
                "records_updated": 0,
                "records_skipped": 0,
            }
        },
    }

    with patch("app.ingestion.datagov_connector.DataGovConnector.has_api_key", True), \
         patch("app.repositories.supabase_repository.list_sync_logs", return_value=[recent_fail, old_success]), \
         patch("app.db._cache", {"sync_logs": [recent_fail, old_success]}):
        res = asyncio.run(get_sync_status(is_demo=False))

    assert res["sources"]["data.gov.in"]["status"] == "FAILED"
    assert res["status"] == "failed"
    assert "timed out" in res["sources"]["data.gov.in"]["error"]
    assert res["last_sync"]["id"] == "log-recent-fail"
    assert res["last_successful_sync"]["id"] == "log-old-success"


def test_sync_status_missing_credentials_reports_not_configured():
    import asyncio
    from app.routers.sync import get_sync_status

    with patch("app.ingestion.datagov_connector.DataGovConnector.has_api_key", False), \
         patch("app.ingestion.adzuna_connector.AdzunaConnector.has_credentials", False), \
         patch("app.repositories.supabase_repository.list_sync_logs", return_value=[]), \
         patch("app.db._cache", {"sync_logs": []}):
        res = asyncio.run(get_sync_status(is_demo=False))

    assert res["sources"]["data.gov.in"]["status"] == "NOT_CONFIGURED"
    assert res["sources"]["data.gov.in"]["configured"] is False
    assert "DATA_GOV_API_KEY is not configured" in res["sources"]["data.gov.in"]["error"]
    assert res["sources"]["adzuna"]["status"] == "NOT_CONFIGURED"
    assert res["sources"]["adzuna"]["configured"] is False
    assert "ADZUNA_APP_ID" in res["sources"]["adzuna"]["error"]
    assert res["status"] == "degraded"


def test_sync_status_successful_real_ingestion():
    import asyncio
    from app.routers.sync import get_sync_status

    success_log = {
        "id": "log-success-1",
        "source_name": "data.gov.in",
        "status": "success",
        "records_fetched": 30,
        "records_added": 30,
        "records_updated": 0,
        "records_skipped": 0,
        "error_message": None,
        "started_at": "2026-09-12T03:00:00Z",
        "completed_at": "2026-09-12T03:00:03Z",
        "sources_detail": {
            "data.gov.in": {
                "status": "SUCCESS",
                "error": None,
                "records_fetched": 30,
                "records_added": 30,
                "records_updated": 0,
                "records_skipped": 0,
            }
        },
    }

    with patch("app.ingestion.datagov_connector.DataGovConnector.has_api_key", True), \
         patch("app.repositories.supabase_repository.list_sync_logs", return_value=[success_log]), \
         patch("app.db._cache", {"sync_logs": [success_log]}):
        res = asyncio.run(get_sync_status(is_demo=False))

    assert res["sources"]["data.gov.in"]["status"] == "SUCCESS"
    assert res["sources"]["data.gov.in"]["records_fetched"] == 30
    assert res["sources"]["data.gov.in"]["error"] is None
    assert res["status"] == "healthy"


def test_sync_status_demo_mode_isolated():
    import asyncio
    from app.routers.sync import get_sync_status

    res = asyncio.run(get_sync_status(is_demo=True))
    assert res["status"] == "healthy"
    assert res["sources"]["data.gov.in"]["status"] == "SUCCESS"
    assert res["sources"]["adzuna"]["status"] == "SUCCESS"
    assert res["sources"]["data.gov.in"]["configured"] is True
    assert res["sources"]["adzuna"]["configured"] is True


def test_sync_log_persistence_encoding_and_decoding():
    from app.db import save_sync_log, decode_sync_log

    entry = {
        "id": "test-encode-id-1",
        "source_name": "data.gov.in",
        "job_type": "scheduled_sync",
        "status": "failed",
        "records_fetched": 0,
        "records_added": 0,
        "records_updated": 0,
        "records_skipped": 0,
        "error_message": "data.gov.in: FAILED - 500 server error",
        "started_at": "2026-09-12T04:00:00Z",
        "completed_at": "2026-09-12T04:00:01Z",
        "duration_ms": 150,
        "sources_detail": {
            "data.gov.in": {
                "status": "FAILED",
                "error": "500 server error",
                "records_fetched": 0,
                "records_added": 0,
                "records_updated": 0,
                "records_skipped": 0,
            }
        },
    }

    mock_client = MagicMock()
    with patch("app.db.get_supabase_client", return_value=mock_client):
        save_sync_log(entry)
        assert mock_client.table.called
        upsert_call = mock_client.table("sync_logs").upsert.call_args[0][0]
        assert "||SOURCES_DETAIL:" in upsert_call["error_message"]

    decoded = decode_sync_log(upsert_call)
    assert decoded["error_message"] == "data.gov.in: FAILED - 500 server error"
    assert decoded["sources_detail"]["data.gov.in"]["status"] == "FAILED"
    assert decoded["sources_detail"]["data.gov.in"]["error"] == "500 server error"


def test_sync_routes_filter_mixed_persisted_demo_and_real_logs():
    import asyncio
    import json
    from app.routers.sync import get_sync_logs, get_sync_status

    raw_demo_log = {
        "id": "persisted-demo-1",
        "source_name": "data.gov.in",
        "job_type": "scheduled_sync",
        "status": "success",
        "records_fetched": 100,
        "error_message": "||SOURCES_DETAIL:" + json.dumps({"_meta": {"is_demo": True}, "data.gov.in": {"status": "SUCCESS", "records_fetched": 100}}),
        "started_at": "2026-09-12T05:00:00Z",
        "completed_at": "2026-09-12T05:00:01Z",
    }
    raw_real_log = {
        "id": "persisted-real-1",
        "source_name": "data.gov.in",
        "job_type": "scheduled_sync",
        "status": "failed",
        "records_fetched": 0,
        "error_message": "data.gov.in: FAILED - 403 Forbidden||SOURCES_DETAIL:" + json.dumps({"_meta": {"is_demo": False}, "data.gov.in": {"status": "FAILED", "error": "403 Forbidden", "records_fetched": 0}}),
        "started_at": "2026-09-12T05:01:00Z",
        "completed_at": "2026-09-12T05:01:02Z",
    }

    with patch("app.ingestion.datagov_connector.DataGovConnector.has_api_key", True), \
         patch("app.repositories.supabase_repository.list_sync_logs", return_value=[raw_real_log, raw_demo_log]), \
         patch("app.db._cache", {"sync_logs": [raw_real_log, raw_demo_log]}):
        logs = asyncio.run(get_sync_logs(limit=20, offset=0, is_demo=False))
        status = asyncio.run(get_sync_status(is_demo=False))

    assert len(logs) == 1
    assert logs[0]["id"] == "persisted-real-1"
    assert status["status"] == "failed"
    assert status["sources"]["data.gov.in"]["status"] == "FAILED"
    assert status["last_sync"]["id"] == "persisted-real-1"


def test_list_sync_logs_overfetches_and_filters_demo_logs_before_limit():
    import json
    from app.repositories.supabase_repository import list_sync_logs
    demo_rows = [
        {
            "id": f"demo-{i}",
            "source_name": "data.gov.in",
            "job_type": "scheduled_sync",
            "status": "success",
            "records_fetched": 100,
            "error_message": "||SOURCES_DETAIL:" + json.dumps({"_meta": {"is_demo": True}}),
            "started_at": f"2026-09-12T10:{i:02d}:00Z",
            "completed_at": f"2026-09-12T10:{i:02d}:01Z",
        }
        for i in range(12)
    ]
    real_rows = [
        {
            "id": "real-running-1",
            "source_name": "data.gov.in",
            "job_type": "scheduled_sync",
            "status": "running",
            "records_fetched": 0,
            "error_message": "||SOURCES_DETAIL:" + json.dumps({"_meta": {"is_demo": False}}),
            "started_at": "2026-09-12T09:59:00Z",
        },
        {
            "id": "real-success-2",
            "source_name": "data.gov.in",
            "job_type": "scheduled_sync",
            "status": "success",
            "records_fetched": 50,
            "error_message": "||SOURCES_DETAIL:" + json.dumps({"_meta": {"is_demo": False}}),
            "started_at": "2026-09-12T09:00:00Z",
            "completed_at": "2026-09-12T09:00:05Z",
        },
    ]
    all_rows = demo_rows + real_rows

    mock_client = MagicMock()
    mock_query = MagicMock()
    mock_client.table.return_value.select.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_res = MagicMock()
    mock_res.data = all_rows
    mock_query.execute.return_value = mock_res

    with patch("app.repositories.supabase_repository.get_client", return_value=mock_client):
        single_real = list_sync_logs(limit=1, is_demo=False)
        assert len(single_real) == 1
        assert single_real[0]["id"] == "real-running-1"
        assert single_real[0]["is_demo"] is False
        mock_query.limit.assert_called_with(50)

        all_real = list_sync_logs(limit=10, is_demo=False)
        assert len(all_real) == 2
        assert [r["id"] for r in all_real] == ["real-running-1", "real-success-2"]

        top_demo = list_sync_logs(limit=5, is_demo=True)
        assert len(top_demo) == 5
        assert all(r["is_demo"] is True for r in top_demo)
