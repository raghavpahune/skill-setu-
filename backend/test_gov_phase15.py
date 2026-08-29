"""Tests for Phase 15: Government Schemes & Opportunities module."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
ADMIN_KEY = "demo-admin-key-2026"


def test_list_gov_opportunities():
    """Verify list_gov_opportunities endpoint returns opportunities with proper structure."""
    res = client.get("/api/gov/opportunities")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0

    first = data[0]
    assert "id" in first
    assert "name" in first
    assert "department" in first
    assert "opportunity_type" in first
    assert "source" in first
    assert "last_updated" in first
    assert first["source"] == "DEMO_SYNTHETIC"


def test_gov_opportunities_filtering_by_type_and_district():
    """Verify filtering by opportunity_type and district."""
    res = client.get("/api/gov/opportunities?opportunity_type=apprenticeship")
    assert res.status_code == 200
    data = res.json()
    for opp in data:
        assert opp["opportunity_type"] == "apprenticeship"

    res_district = client.get("/api/gov/opportunities?district=Pune")
    assert res_district.status_code == 200
    pune_data = res_district.json()
    assert len(pune_data) > 0


def test_gov_opportunities_search():
    """Verify search filter on name/department/description."""
    res = client.get("/api/gov/opportunities?q=Fitter")
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0
    assert any("fitter" in d["name"].lower() or "fitter" in d.get("description", "").lower() for d in data)


def test_gov_opportunity_types_metadata():
    """Verify distinct opportunity types and metadata."""
    res = client.get("/api/gov/opportunities/types")
    assert res.status_code == 200
    data = res.json()
    assert "opportunity_types" in data
    assert "districts" in data
    assert "skills" in data
    assert "total" in data
    assert len(data["opportunity_types"]) > 0


def test_get_individual_gov_opportunity():
    """Verify single opportunity lookup and 404 behavior."""
    res = client.get("/api/gov/opportunities/gov-001")
    assert res.status_code == 200
    assert res.json()["id"] == "gov-001"

    res_404 = client.get("/api/gov/opportunities/non-existent-id")
    assert res_404.status_code == 404


def test_recommended_gov_opportunities():
    """Verify student profile matching returns scored opportunities with match reasons."""
    res = client.get("/api/gov/opportunities/recommended/stu-001")
    assert res.status_code == 200
    data = res.json()
    assert data["student_id"] == "stu-001"
    assert "opportunities" in data
    assert "provenance_note" in data
    assert len(data["opportunities"]) > 0

    first = data["opportunities"][0]
    assert "relevance_score" in first
    assert "match_reasons" in first
    assert len(first["match_reasons"]) > 0


def test_recommended_schemes():
    """Verify schemes recommendation endpoint returns scored schemes with match reasons."""
    res = client.get("/api/schemes/recommended/stu-001")
    assert res.status_code == 200
    data = res.json()
    assert data["student_id"] == "stu-001"
    assert "schemes" in data
    assert "provenance_note" in data
    assert len(data["schemes"]) > 0

    first = data["schemes"][0]
    assert "relevance_score" in first
    assert "match_reasons" in first
    assert "source" in first
    assert "last_updated" in first


def test_admin_gov_opportunities_auth_required():
    """Verify admin endpoint rejects requests without admin key."""
    res = client.get("/api/admin/gov/opportunities")
    assert res.status_code == 401

    res_invalid = client.get("/api/admin/gov/opportunities", headers={"X-Admin-Key": "wrong-key"})
    assert res_invalid.status_code == 401


def test_admin_gov_opportunities_crud():
    """Verify admin can list, create, update, and delete government opportunities."""
    headers = {"X-Admin-Key": ADMIN_KEY}

    # 1. List
    res_list = client.get("/api/admin/gov/opportunities", headers=headers)
    assert res_list.status_code == 200
    data = res_list.json()
    assert data["status"] == "success"
    assert "total" in data
    assert "active_count" in data
    assert "demo_count" in data

    # 2. Create
    new_opp = {
        "name": "Automated Test Solar Technician Training",
        "department": "Maharashtra Energy Development Agency (MEDA)",
        "description": "Short-term hands-on skill training in solar PV installation and maintenance.",
        "eligibility_criteria": "10th pass or ITI Electrical; Maharashtra resident",
        "target_skills": ["Solar", "Electrical", "Renewable Energy"],
        "district_coverage": "State-wide (Maharashtra)",
        "opportunity_type": "training_program",
        "application_url": "https://www.meda.maharashtra.gov.in",
        "deadline": "2027-12-31",
        "status": "active"
    }
    res_create = client.post("/api/admin/gov/opportunities", headers=headers, json=new_opp)
    assert res_create.status_code == 200
    created = res_create.json()["opportunity"]
    opp_id = created["id"]
    assert created["source"] == "ADMIN_CREATED"
    assert created["is_demo"] is False
    assert created["name"] == new_opp["name"]

    # 3. Update
    res_update = client.patch(
        f"/api/admin/gov/opportunities/{opp_id}",
        headers=headers,
        json={"status": "inactive"}
    )
    assert res_update.status_code == 200
    updated = res_update.json()["opportunity"]
    assert updated["status"] == "inactive"

    # 4. Delete
    res_delete = client.delete(f"/api/admin/gov/opportunities/{opp_id}", headers=headers)
    assert res_delete.status_code == 200
    assert res_delete.json()["status"] == "success"

    # Verify deleted
    res_get = client.get(f"/api/gov/opportunities/{opp_id}")
    assert res_get.status_code == 404
