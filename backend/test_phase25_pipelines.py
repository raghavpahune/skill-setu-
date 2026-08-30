"""Phase 25 Backend Tests — Employer & Institute Data Pipeline & RBAC Isolation.

Covers:
1. Employer authentication & submission validation (POST /api/employer/demands)
2. Employer ownership isolation (Employer A vs Employer B 403, Student 403, Anonymous 401)
3. Employer my-demands listing, update, and deletion
4. Institute authentication & course submission (POST /api/institute/courses)
5. Institute ownership isolation (Institute A vs Institute B 403, Student/Employer 403, Anonymous 401)
6. Institute my-courses listing, update, and deletion
7. Admin management for institute courses (GET, PATCH, DELETE /api/admin/institute/courses)
8. Provenance preservation (USER_SUBMITTED vs DEMO_SYNTHETIC)
9. Recommendation Engine data pipeline integration with matched institute training courses
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token
from app.db import get_demo, init_demo_users


@pytest.fixture(scope="module")
def client():
    init_demo_users()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def student_token():
    return create_access_token({"sub": "usr-student-001", "email": "student@skillsetu.gov.in", "role": "STUDENT"})


@pytest.fixture
def employer1_token():
    return create_access_token({
        "sub": "usr-employer-001",
        "email": "employer@skillsetu.gov.in",
        "role": "EMPLOYER",
        "organization_id": "emp-001",
    })


@pytest.fixture
def employer2_token():
    return create_access_token({
        "sub": "usr-employer-002",
        "email": "employer2@skillsetu.gov.in",
        "role": "EMPLOYER",
        "organization_id": "emp-002",
    })


@pytest.fixture
def institute1_token():
    return create_access_token({
        "sub": "usr-institute-001",
        "email": "institute@skillsetu.gov.in",
        "role": "INSTITUTE",
        "organization_id": "inst-coep",
    })


@pytest.fixture
def institute2_token():
    return create_access_token({
        "sub": "usr-institute-002",
        "email": "institute2@skillsetu.gov.in",
        "role": "INSTITUTE",
        "organization_id": "inst-vjti",
    })


@pytest.fixture
def admin_token():
    return create_access_token({"sub": "usr-admin-001", "email": "admin@skillsetu.gov.in", "role": "ADMIN"})


# ============================================================================
# 1. EMPLOYER DATA PIPELINE TESTS
# ============================================================================

def test_employer_demand_submission_unauthenticated(client):
    """Anonymous users cannot submit employer hiring demands (401)."""
    res = client.post("/api/employer/demands", json={
        "company_name": "Tata Motors",
        "industry": "Automotive",
        "district": "Pune",
        "job_role": "EV Powertrain Engineer",
        "required_skills": ["Battery Management", "Motor Control"],
    })
    assert res.status_code == 401


def test_employer_demand_submission_forbidden_roles(client, student_token, institute1_token):
    """Students and Institutes cannot submit employer hiring demands (403)."""
    payload = {
        "company_name": "Tata Motors",
        "industry": "Automotive",
        "district": "Pune",
        "job_role": "EV Powertrain Engineer",
        "required_skills": ["Battery Management", "Motor Control"],
    }
    res_student = client.post("/api/employer/demands", json=payload, headers={"Authorization": f"Bearer {student_token}"})
    assert res_student.status_code == 403

    res_inst = client.post("/api/employer/demands", json=payload, headers={"Authorization": f"Bearer {institute1_token}"})
    assert res_inst.status_code == 403


def test_employer_demand_submission_success_and_provenance(client, employer1_token):
    """Authenticated Employer can submit hiring demand and receives USER_SUBMITTED provenance."""
    payload = {
        "company_name": "Tata Motors Innovation Lab",
        "industry": "Electric Vehicles",
        "district": "Pune",
        "job_role": "High-Voltage EV Battery Engineer",
        "required_skills": ["Battery Management (BMS)", "CAN Bus", "High-Voltage Diagnostics"],
        "openings_count": 25,
        "nsqf_level": 6,
        "experience_level": "Entry Level (0-1 yrs)",
        "hiring_timeline": "Immediate (0-30 days)",
        "additional_requirements": "Hands-on experience with hardware-in-the-loop (HIL) simulators.",
    }
    res = client.post("/api/employer/demands", json=payload, headers={"Authorization": f"Bearer {employer1_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "created"
    demand = data["demand"]
    assert demand["company_name"] == "Tata Motors Innovation Lab"
    assert demand["source"] == "EMPLOYER_SUBMITTED"
    assert demand["is_demo"] is False
    assert demand["validation_status"] == "PENDING"
    assert "id" in demand


def test_employer_my_demands_and_ownership_isolation(client, employer1_token, employer2_token):
    """Employer 1 can see own demands; Employer 2 cannot modify or delete Employer 1's demands."""
    # 1. Submit demand as Employer 1
    create_res = client.post("/api/employer/demands", json={
        "company_name": "Employer One Tech",
        "industry": "IT & Software",
        "district": "Pune",
        "job_role": "Senior Cloud Infrastructure Architect",
        "required_skills": ["Kubernetes", "AWS", "Terraform"],
        "openings_count": 8,
    }, headers={"Authorization": f"Bearer {employer1_token}"})
    demand_id = create_res.json()["demand"]["id"]

    # 2. Employer 1 can fetch their own demands
    mine_res = client.get("/api/employer/my-demands", headers={"Authorization": f"Bearer {employer1_token}"})
    assert mine_res.status_code == 200
    my_ids = [d["id"] for d in mine_res.json()["demands"]]
    assert demand_id in my_ids

    # 3. Employer 2 attempts to patch Employer 1's demand -> 403 Forbidden
    patch_res = client.patch(f"/api/employer/demands/{demand_id}", json={
        "job_role": "Hijacked Role Title",
    }, headers={"Authorization": f"Bearer {employer2_token}"})
    assert patch_res.status_code == 403

    # 4. Employer 2 attempts to delete Employer 1's demand -> 403 Forbidden
    del_res = client.delete(f"/api/employer/demands/{demand_id}", headers={"Authorization": f"Bearer {employer2_token}"})
    assert del_res.status_code == 403

    # 5. Employer 1 successfully updates their own demand
    update_res = client.patch(f"/api/employer/demands/{demand_id}", json={
        "job_role": "Updated Lead Cloud Architect",
        "openings_count": 12,
    }, headers={"Authorization": f"Bearer {employer1_token}"})
    assert update_res.status_code == 200
    assert update_res.json()["demand"]["job_role"] == "Updated Lead Cloud Architect"

    # 6. Employer 1 successfully deletes their own demand
    own_del_res = client.delete(f"/api/employer/demands/{demand_id}", headers={"Authorization": f"Bearer {employer1_token}"})
    assert own_del_res.status_code == 200


# ============================================================================
# 2. INSTITUTE DATA PIPELINE TESTS
# ============================================================================

def test_institute_course_submission_unauthenticated(client):
    """Anonymous users cannot submit training programs (401)."""
    res = client.post("/api/institute/courses", json={
        "name": "Diploma in Industrial Robotics",
        "district": "Pune",
        "skills": ["PLC Programming", "SCADA"],
    })
    assert res.status_code == 401


def test_institute_course_submission_forbidden_roles(client, student_token, employer1_token):
    """Students and Employers cannot submit institute courses (403)."""
    payload = {
        "name": "Diploma in Industrial Robotics",
        "district": "Pune",
        "skills": ["PLC Programming", "SCADA"],
    }
    res_student = client.post("/api/institute/courses", json=payload, headers={"Authorization": f"Bearer {student_token}"})
    assert res_student.status_code == 403

    res_emp = client.post("/api/institute/courses", json=payload, headers={"Authorization": f"Bearer {employer1_token}"})
    assert res_emp.status_code == 403


def test_institute_course_submission_success_and_provenance(client, institute1_token):
    """Authenticated Institute can submit accredited training program with proper provenance."""
    payload = {
        "name": "Advanced EV Battery Diagnostics & BMS Testing",
        "institute_name": "Government Polytechnic Pune",
        "district": "Pune",
        "category": "Automotive & Clean Energy",
        "description": "Comprehensive practical lab curriculum for EV powertrains and high-voltage battery safety.",
        "skills": ["EV Battery Technology", "Battery Management (BMS)", "CAN Bus"],
        "nsqf_level": 6,
        "enrolment_capacity": 60,
        "placed_count": 52,
        "duration_weeks": 16,
        "certifications": "MSBTE & DGT Certificate in Clean Energy",
    }
    res = client.post("/api/institute/courses", json=payload, headers={"Authorization": f"Bearer {institute1_token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "created"
    course = data["course"]
    assert course["name"] == "Advanced EV Battery Diagnostics & BMS Testing"
    assert course["source"] == "USER_SUBMITTED"
    assert course["is_demo"] is False
    assert course["data_provenance"] == "INSTITUTE_REPORTED"
    assert course["placement_rate"] == 87  # round(52 / 60 * 100)


def test_institute_my_courses_and_ownership_isolation(client, institute1_token, institute2_token):
    """Institute 1 can manage own courses; Institute 2 cannot edit or delete Institute 1's courses."""
    # 1. Create course as Institute 1
    create_res = client.post("/api/institute/courses", json={
        "name": "Robotics Process Automation (RPA) Lab",
        "district": "Pune",
        "skills": ["Robotics", "Python", "Automation"],
        "enrolment_capacity": 40,
        "placed_count": 35,
    }, headers={"Authorization": f"Bearer {institute1_token}"})
    course_id = create_res.json()["course"]["id"]

    # 2. Institute 1 can list own courses
    mine_res = client.get("/api/institute/my-courses", headers={"Authorization": f"Bearer {institute1_token}"})
    assert mine_res.status_code == 200
    my_ids = [c["id"] for c in mine_res.json()["courses"]]
    assert course_id in my_ids

    # 3. Institute 2 attempts to patch Institute 1's course -> 403 Forbidden
    patch_res = client.patch(f"/api/institute/courses/{course_id}", json={
        "name": "Tampered Course Name",
    }, headers={"Authorization": f"Bearer {institute2_token}"})
    assert patch_res.status_code == 403

    # 4. Institute 2 attempts to delete Institute 1's course -> 403 Forbidden
    del_res = client.delete(f"/api/institute/courses/{course_id}", headers={"Authorization": f"Bearer {institute2_token}"})
    assert del_res.status_code == 403

    # 5. Institute 1 successfully updates own course
    update_res = client.patch(f"/api/institute/courses/{course_id}", json={
        "name": "Robotics & Smart Factory Automation Lab",
        "enrolment_capacity": 50,
        "placed_count": 45,
    }, headers={"Authorization": f"Bearer {institute1_token}"})
    assert update_res.status_code == 200
    assert update_res.json()["course"]["name"] == "Robotics & Smart Factory Automation Lab"
    assert update_res.json()["course"]["placement_rate"] == 90

    # 6. Institute 1 successfully deletes own course
    del_own_res = client.delete(f"/api/institute/courses/{course_id}", headers={"Authorization": f"Bearer {institute1_token}"})
    assert del_own_res.status_code == 200


# ============================================================================
# 3. ADMIN MANAGEMENT FOR COURSES TESTS
# ============================================================================

def test_admin_course_management(client, admin_token, student_token, institute1_token):
    """Admin has full authority to list, audit, and delete institute courses; Non-admin receives 403."""
    # 1. Non-admin accessing admin courses -> 403
    non_admin_res = client.get("/api/admin/institute/courses", headers={"Authorization": f"Bearer {student_token}"})
    assert non_admin_res.status_code == 403

    # 2. Admin lists courses
    admin_res = client.get("/api/admin/institute/courses", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_res.status_code == 200
    data = admin_res.json()
    assert "total" in data
    assert "user_submitted_count" in data
    assert "demo_synthetic_count" in data

    # 3. Admin can update and delete any course
    # Create test course as Institute 1
    create_res = client.post("/api/institute/courses", json={
        "name": "Admin Audit Target Course",
        "district": "Nagpur",
        "skills": ["Solar PV", "Grid Integration"],
    }, headers={"Authorization": f"Bearer {institute1_token}"})
    course_id = create_res.json()["course"]["id"]

    # Admin updates status
    patch_res = client.patch(f"/api/admin/institute/courses/{course_id}", json={
        "status": "needs_attention",
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert patch_res.status_code == 200
    assert patch_res.json()["course"]["status"] == "needs_attention"

    # Admin deletes course
    del_res = client.delete(f"/api/admin/institute/courses/{course_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert del_res.status_code == 200


# ============================================================================
# 4. RECOMMENDATION ENGINE & DATA PIPELINE INTEGRATION
# ============================================================================

def test_recommendation_engine_connects_institute_training(client):
    """Recommendation engine matches student missing skills to active institute training programs."""
    from app.services.career_recommendation_engine import compute_career_recommendations

    # Compute recommendations for standard student profile
    res = compute_career_recommendations("stu-001")
    assert res["status"] == "success"
    assert "recommended_careers" in res
    assert "personalized_roadmap" in res

    # Verify career evaluations include matched institute training programs
    top_career = res["top_recommendation"]
    assert "matched_institute_training" in top_career
    assert isinstance(top_career["matched_institute_training"], list)

    # Verify roadmap steps include matched institute training courses
    roadmap = res["personalized_roadmap"]
    assert len(roadmap) > 0
    first_step = roadmap[0]
    assert "matched_institute_training" in first_step
    assert "skill_name" in first_step
    assert "action_item" in first_step
