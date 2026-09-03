"""Phase 34: Dedicated tests for Employer Identity Verification & Institute Syllabus Ingestion."""
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.services.employer_verification import (
    validate_gstin,
    is_corporate_domain,
    verify_employer_credentials,
)
from app.services.syllabus_extractor import (
    extract_skills_from_syllabus,
    extract_raw_text_from_pdf,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. GSTIN & Corporate Domain Verification Unit Tests
# ---------------------------------------------------------------------------

def test_validate_gstin_valid_maharashtra():
    res = validate_gstin("27AABCU9603R1ZN")
    assert res["valid"] is True
    assert res["state_code"] == "27"
    assert res["state_name"] == "Maharashtra"
    assert res["is_maharashtra"] is True
    assert res["pan"] == "AABCU9603R"


def test_validate_gstin_valid_karnataka():
    res = validate_gstin("29AABCU9603R1ZN")
    assert res["valid"] is True
    assert res["state_code"] == "29"
    assert res["state_name"] == "Karnataka"
    assert res["is_maharashtra"] is False


def test_validate_gstin_invalid_formats():
    assert validate_gstin(None)["valid"] is False
    assert validate_gstin("")["valid"] is False
    assert validate_gstin("SHORT")["valid"] is False
    assert validate_gstin("INVALID_15_CHARS")["valid"] is False


def test_is_corporate_domain():
    is_corp, domain = is_corporate_domain("contact@tatamotors.com")
    assert is_corp is True
    assert domain == "tatamotors.com"

    is_corp, domain = is_corporate_domain("recruiter@mahindra.co.in")
    assert is_corp is True

    is_corp, domain = is_corporate_domain("someone@gmail.com")
    assert is_corp is False
    assert domain == "gmail.com"

    is_corp, domain = is_corporate_domain("test@yahoo.com")
    assert is_corp is False


def test_verify_employer_credentials_tiers():
    # Tier 1: Valid GSTIN + Corporate Email
    t1 = verify_employer_credentials("careers@tatamotors.com", gstin="27AABCU9603R1ZN")
    assert t1["verified"] is True
    assert t1["verification_tier"] == "ENTERPRISE_VERIFIED"
    assert "Verified Enterprise" in t1["badge"]

    # Tier 2: Corporate Email Only
    t2 = verify_employer_credentials("careers@tatamotors.com", gstin=None)
    assert t2["verified"] is True
    assert t2["verification_tier"] == "CORPORATE_DOMAIN_VERIFIED"

    # Tier 3: Valid GSTIN with generic email
    t3 = verify_employer_credentials("business_owner@gmail.com", gstin="27AABCU9603R1ZN")
    assert t3["verified"] is True
    assert t3["verification_tier"] == "GSTIN_VERIFIED"

    # Tier 4: Generic email and no GSTIN
    t4 = verify_employer_credentials("random@gmail.com", gstin=None)
    assert t4["verified"] is False
    assert t4["verification_tier"] == "STANDARD_UNVERIFIED"


# ---------------------------------------------------------------------------
# 2. Employer Identity API Tests
# ---------------------------------------------------------------------------

def test_api_employer_verify_identity():
    # Unauthenticated / with token check
    resp = client.post(
        "/api/employer/verify-identity",
        json={
            "email": "hr@tatamotors.com",
            "gstin": "27AABCU9603R1ZN",
            "company_name": "Tata Motors Ltd",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["verified"] is True
    assert data["verification_tier"] == "ENTERPRISE_VERIFIED"
    assert data["is_corporate_email"] is True
    assert data["gstin_details"]["state_name"] == "Maharashtra"


def test_api_employer_demand_submission_with_gstin():
    # Login as employer
    login_resp = client.post(
        "/api/auth/login",
        json={"email": "employer@skillsetu.gov.in", "password": "Password@123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    demand_payload = {
        "company_name": "Bharat EV Solutions Ltd",
        "industry": "Electric Vehicles",
        "district": "Pune",
        "job_role": "EV Battery Integration Specialist",
        "required_skills": ["EV Battery Technology", "Python"],
        "gstin": "27AABCU9603R1ZN",
        "positions_count": 5,
        "experience_level": "Mid Level (2-5 yrs)",
        "hiring_timeline": "Immediate (0-30 days)",
    }

    sub_resp = client.post(
        "/api/employer/demand",
        json=demand_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert sub_resp.status_code == 200
    sub_data = sub_resp.json()
    demand = sub_data["demand"]

    assert demand["gstin"] == "27AABCU9603R1ZN"
    assert demand["is_verified"] is True
    assert demand["verification_tier"] in ("ENTERPRISE_VERIFIED", "GSTIN_VERIFIED")


# ---------------------------------------------------------------------------
# 3. Institute Syllabus Ingestion & NLP Extraction Tests
# ---------------------------------------------------------------------------

def test_extract_skills_from_plain_text():
    sample_syllabus = """
    Department of Computer Science & Engineering
    Advanced Vocational Program in Generative AI & Cloud Architecture

    Course Outline:
    Module 1: Introduction to Python Programming and Statistical Analysis.
    Module 2: Machine Learning fundamentals, Deep Learning, and Neural Networks.
    Module 3: Generative AI and Large Language Models, Prompt Engineering, RAG Pipelines.
    Module 4: Deploying AI Agents on Cloud Infrastructure using AWS and Kubernetes.
    Module 5: Relational database queries using SQL and Data Engineering.

    Prerequisites: Basic knowledge of Java and algorithms.
    """

    res = extract_skills_from_syllabus(sample_syllabus, course_name_hint="AI Systems Engineering")
    assert res["status"] == "success"
    assert res["skills_count"] >= 5

    # Check key taxonomy skills matched
    extracted = set(res["extracted_skills"])
    assert "Python" in extracted
    assert "Machine Learning" in extracted
    assert "Generative AI" in extracted
    assert "SQL" in extracted
    assert "AWS" in extracted

    # Check suggestions
    assert res["suggested_nsqf_level"] >= 5
    assert res["suggested_category"] in ("AI/ML", "Cloud", "Data Science", "Programming")
    assert res["suggested_course_name"] == "AI Systems Engineering"


def test_extract_skills_from_manufacturing_text():
    mfg_syllabus = """
    Advanced Certificate in Precision Industrial Automation
    Topics Covered:
    - CNC Programming and Machining operations
    - PLC Programming with Ladder Logic
    - Industrial Robotics and Mechatronics integration
    - Arc Welding and Electrical Maintenance
    """

    res = extract_skills_from_syllabus(mfg_syllabus)
    assert res["status"] == "success"
    extracted = set(res["extracted_skills"])
    assert "CNC Programming" in extracted
    assert "PLC Programming" in extracted
    assert "Robotics" in extracted
    assert res["suggested_category"] == "Manufacturing"


def test_api_institute_syllabus_extract_json():
    # Login as institute
    login_resp = client.post(
        "/api/auth/login",
        json={"email": "institute@skillsetu.gov.in", "password": "Password@123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    payload = {
        "syllabus_text": "Syllabus covers EV Battery Technology, EV Motor Design, AutoCAD, and IoT.",
        "course_name": "EV Mobility Diploma",
    }

    resp = client.post(
        "/api/institute/syllabus/extract",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "EV Battery Technology" in data["extracted_skills"]
    assert "AutoCAD" in data["extracted_skills"]
    assert data["suggested_nsqf_level"] >= 4


def test_api_institute_syllabus_extract_empty_fails():
    resp = client.post(
        "/api/institute/syllabus/extract",
        json={"syllabus_text": ""},
    )
    assert resp.status_code in (400, 422)
