import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.ingestion.industry_intelligence import industry_ingestor
from app.repositories import supabase_repository

client = TestClient(app)


def test_industry_signals_endpoint_returns_signals():
    res = client.get("/api/industry/signals?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert data.get("status") == "success"
    assert "signals" in data
    assert isinstance(data["signals"], list)
    assert len(data["signals"]) > 0

    first = data["signals"][0]
    assert "id" in first
    assert "title" in first
    assert "skills" in first
    assert isinstance(first["skills"], list)


def test_industry_signals_filter_by_industry():
    res = client.get("/api/industry/signals?industry=Automotive")
    assert res.status_code == 200
    data = res.json()
    assert data.get("status") == "success"
    assert "signals" in data


def test_legacy_signals_endpoint_compatibility():
    res = client.get("/api/signals")
    assert res.status_code == 200
    signals = res.json()
    assert isinstance(signals, list)
    assert len(signals) > 0
    assert "title" in signals[0]


def test_industry_intelligence_ingestor_executes():
    summary = industry_ingestor.ingest_from_feeds()
    assert summary["status"] in ("success", "partial_success")
    assert summary["records_fetched"] > 0
