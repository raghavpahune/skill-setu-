import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from app.core.time import parse_iso_timestamp, UTC_MIN
from app.services.roadmap_service import _extract_student_skills, _get_target_role
from app.repositories.supabase_repository import get_employee_profile, SupabaseRepositoryError
from app.config import settings


def test_parse_iso_timestamp_z():
    res = parse_iso_timestamp("2026-09-10T12:00:00Z")
    assert res == datetime(2026, 9, 10, 12, 0, 0, tzinfo=timezone.utc)


def test_parse_iso_timestamp_offset():
    res = parse_iso_timestamp("2026-09-10T12:00:00+05:30")
    assert res.tzinfo is not None


def test_parse_iso_timestamp_naive():
    res = parse_iso_timestamp("2026-09-10T12:00:00")
    assert res == datetime(2026, 9, 10, 12, 0, 0, tzinfo=timezone.utc)


def test_parse_iso_timestamp_invalid():
    assert parse_iso_timestamp("") == UTC_MIN
    assert parse_iso_timestamp("not-a-timestamp") == UTC_MIN
    assert parse_iso_timestamp(None) == UTC_MIN


def test_roadmap_skills_newer_profile_wins():
    profile = {
        "updated_at": "2026-09-10T12:00:00Z",
        "skills": [
            {"skill_id": "sk-001", "name": "Python", "proficiency": "beginner"},
            {"skill_id": "sk-002", "name": "SQL", "proficiency": "intermediate"},
        ]
    }
    assessment = {
        "updated_at": "2026-09-08T12:00:00Z",
        "current_skills": [
            {"skill_id": "sk-001", "skill_name": "Python", "proficiency": "expert"},
            {"skill_id": "sk-003", "skill_name": "Docker", "proficiency": "advanced"},
        ]
    }

    skills_by_id = {
        "sk-001": {"id": "sk-001", "name": "Python", "category": "Tech", "nsqf_level": 5},
        "sk-002": {"id": "sk-002", "name": "SQL", "category": "Tech", "nsqf_level": 4},
        "sk-003": {"id": "sk-003", "name": "Docker", "category": "DevOps", "nsqf_level": 6},
    }
    skills_by_name = {
        "python": skills_by_id["sk-001"],
        "sql": skills_by_id["sk-002"],
        "docker": skills_by_id["sk-003"],
    }

    skills = _extract_student_skills(profile, assessment, skills_by_id, skills_by_name)
    assert skills["sk-001"]["proficiency"] == "beginner"
    assert skills["sk-002"]["proficiency"] == "intermediate"
    assert skills["sk-003"]["proficiency"] == "advanced"


def test_roadmap_skills_newer_assessment_wins():
    profile = {
        "updated_at": "2026-09-05T12:00:00Z",
        "skills": [
            {"skill_id": "sk-001", "name": "Python", "proficiency": "expert"},
        ]
    }
    assessment = {
        "updated_at": "2026-09-09T12:00:00Z",
        "current_skills": [
            {"skill_id": "sk-001", "skill_name": "Python", "proficiency": "beginner"},
            {"skill_id": "sk-004", "skill_name": "Kubernetes", "proficiency": "intermediate"},
        ]
    }

    skills_by_id = {
        "sk-001": {"id": "sk-001", "name": "Python", "category": "Tech", "nsqf_level": 5},
        "sk-004": {"id": "sk-004", "name": "Kubernetes", "category": "DevOps", "nsqf_level": 7},
    }
    skills_by_name = {
        "python": skills_by_id["sk-001"],
        "kubernetes": skills_by_id["sk-004"],
    }

    skills = _extract_student_skills(profile, assessment, skills_by_id, skills_by_name)
    assert skills["sk-001"]["proficiency"] == "beginner"
    assert skills["sk-004"]["proficiency"] == "intermediate"


def test_roadmap_get_target_role_precedence():
    profile = {
        "updated_at": "2026-09-10T10:00:00Z",
        "target_role": "Data Scientist",
    }
    assessment = {
        "updated_at": "2026-09-09T10:00:00Z",
        "career_goal": "Cloud Architect",
    }
    assert _get_target_role("student_1", None, profile, assessment) == "Data Scientist"

    profile["updated_at"] = "2026-09-08T10:00:00Z"
    assert _get_target_role("student_1", None, profile, assessment) == "Cloud Architect"


def test_get_employee_profile_demo_fallback_on_connection_error():
    with patch("app.repositories.supabase_repository.get_client") as mock_client:
        mock_client.side_effect = Exception("Supabase connection refused")
        with patch.object(settings, "use_demo_data", True):
            with patch("app.db._cache", {"employee_profiles": [{"user_id": "emp-demo-001", "name": "Demo Emp"}]}):
                res = get_employee_profile("emp-demo-001")
                assert res is not None
                assert res["name"] == "Demo Emp"

                with pytest.raises(SupabaseRepositoryError):
                    get_employee_profile("usr-real-prod-999")
