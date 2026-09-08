import re
import sqlite3
import uuid
from pathlib import Path
import pytest

from app.repositories import supabase_repository
from app.repositories.supabase_repository import (
    create_industry_signal,
    get_industry_signal,
    list_industry_signals,
    update_industry_signal_repo,
    get_student_profile,
    upsert_student_profile,
    delete_student_profile,
)


def _get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def test_migration_sql_has_no_broken_student_skills_type_alteration():
    migration_file = _get_project_root() / "data" / "migrations" / "20260908_production_data_and_rls_hardening.sql"
    content = migration_file.read_text(encoding="utf-8")
    assert "ALTER TABLE student_skills ALTER COLUMN skill_id TYPE TEXT" not in content
    assert "tc.table_name = 'signal_skills'" in content
    assert "ccu.table_name = 'industry_signals'" in content
    assert "signal_skills_signal_id_fkey" in content
    assert "student_skills_skill_id_fkey" in content
    assert "student_skills_user_id_fkey" in content

    users_fk_drop_loop = re.search(
        r"FOR\s+r\s+IN\s*\(\s*SELECT.+?ccu\.table_name\s*=\s*'users'.+?\)\s*LOOP",
        content,
        re.DOTALL,
    )
    assert users_fk_drop_loop is not None
    assert "tc.table_name IN ('student_profiles', 'student_skills', 'employee_profiles')" in users_fk_drop_loop.group(0)


def test_schema_sql_types_align_with_migration():
    schema_file = _get_project_root() / "data" / "schema.sql"
    content = schema_file.read_text(encoding="utf-8")

    signals_match = re.search(r"CREATE TABLE IF NOT EXISTS industry_signals\s*\(\s*id\s+(\w+)", content, re.IGNORECASE)
    assert signals_match is not None
    assert signals_match.group(1).upper() == "TEXT"

    signal_skills_match = re.search(r"CREATE TABLE IF NOT EXISTS signal_skills\s*\(\s*signal_id\s+(\w+)", content, re.IGNORECASE)
    assert signal_skills_match is not None
    assert signal_skills_match.group(1).upper() == "TEXT"

    student_skills_user_match = re.search(r"CREATE TABLE IF NOT EXISTS student_skills\s*\(\s*user_id\s+(\w+)", content, re.IGNORECASE)
    assert student_skills_user_match is not None
    assert student_skills_user_match.group(1).upper() == "TEXT"

    student_skills_skill_match = re.search(r"CREATE TABLE IF NOT EXISTS student_skills\s*\([^;]+skill_id\s+(\w+)", content, re.IGNORECASE)
    assert student_skills_skill_match is not None
    assert student_skills_skill_match.group(1).upper() == "UUID"


def test_sqlite_foreign_key_referential_integrity_and_cascade_lifecycle():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL
        );
    """)

    cursor.execute("""
        CREATE TABLE skills (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL
        );
    """)

    cursor.execute("""
        CREATE TABLE industry_signals (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            source TEXT NOT NULL,
            technology TEXT NOT NULL,
            summary TEXT NOT NULL,
            impact_level TEXT NOT NULL
        );
    """)

    cursor.execute("""
        CREATE TABLE signal_skills (
            signal_id TEXT NOT NULL REFERENCES industry_signals(id) ON DELETE CASCADE,
            skill_id TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
            impact_score INT,
            PRIMARY KEY (signal_id, skill_id)
        );
    """)

    cursor.execute("""
        CREATE TABLE student_profiles (
            user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            full_name TEXT,
            target_role TEXT NOT NULL
        );
    """)

    cursor.execute("""
        CREATE TABLE student_skills (
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            skill_id TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
            proficiency TEXT NOT NULL DEFAULT 'intermediate',
            PRIMARY KEY (user_id, skill_id)
        );
    """)
    conn.commit()

    user_id = str(uuid.uuid4())
    skill_id = str(uuid.uuid4())
    signal_id = "sig-ai-agents-2026"

    cursor.execute("INSERT INTO users (id, name, email, role) VALUES (?, ?, ?, ?)", (user_id, "Dev Student", "dev@skillsetu.gov.in", "STUDENT"))
    cursor.execute("INSERT INTO skills (id, name, category) VALUES (?, ?, ?)", (skill_id, "Python", "Programming"))
    cursor.execute("INSERT INTO industry_signals (id, title, source, technology, summary, impact_level) VALUES (?, ?, ?, ?, ?, ?)", (signal_id, "Agentic AI", "NASSCOM", "AI", "Summary", "critical"))
    cursor.execute("INSERT INTO student_profiles (user_id, full_name, target_role) VALUES (?, ?, ?)", (user_id, "Dev Student", "AI Engineer"))
    cursor.execute("INSERT INTO student_skills (user_id, skill_id, proficiency) VALUES (?, ?, ?)", (user_id, skill_id, "advanced"))
    cursor.execute("INSERT INTO signal_skills (signal_id, skill_id, impact_score) VALUES (?, ?, ?)", (signal_id, skill_id, 9))
    conn.commit()

    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute("INSERT INTO student_skills (user_id, skill_id, proficiency) VALUES (?, ?, ?)", ("non-existent-user", skill_id, "beginner"))

    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute("INSERT INTO student_skills (user_id, skill_id, proficiency) VALUES (?, ?, ?)", (user_id, "non-existent-skill", "beginner"))

    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute("INSERT INTO signal_skills (signal_id, skill_id, impact_score) VALUES (?, ?, ?)", ("non-existent-signal", skill_id, 5))

    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM student_profiles WHERE user_id = ?", (user_id,))
    assert cursor.fetchone()[0] == 0

    cursor.execute("SELECT COUNT(*) FROM student_skills WHERE user_id = ?", (user_id,))
    assert cursor.fetchone()[0] == 0

    cursor.execute("DELETE FROM industry_signals WHERE id = ?", (signal_id,))
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM signal_skills WHERE signal_id = ?", (signal_id,))
    assert cursor.fetchone()[0] == 0

    conn.close()


def test_industry_signals_repository_persistence_with_text_id():
    custom_text_id = f"sig-test-{uuid.uuid4().hex[:10]}"
    sig_payload = {
        "id": custom_text_id,
        "title": "Quantum Safe Cryptography Ingestion",
        "description": "Comprehensive migration to post-quantum algorithms across banking sectors.",
        "category": "EMERGING_SKILL",
        "industry": "Cybersecurity & Cryptography",
        "skills": ["Post-Quantum Cryptography", "Lattice Cryptography"],
        "tools": ["OpenSSL 3.4", "Liboqs"],
        "source_url": "https://nist.gov/pqc",
        "source_name": "NIST National Standards",
        "source_type": "OFFICIAL_GOV",
        "is_active": True,
        "validation_status": "APPROVED",
        "data_provenance": "VERIFIED_EXTERNAL_FEED",
    }
    created = create_industry_signal(sig_payload)
    assert created["id"] == custom_text_id
    assert created["title"] == sig_payload["title"]

    fetched = get_industry_signal(custom_text_id)
    assert fetched is not None
    assert fetched["id"] == custom_text_id

    updated = update_industry_signal_repo(custom_text_id, {"title": "Updated Quantum Title"})
    assert updated["title"] == "Updated Quantum Title"

    signals = list_industry_signals(category="EMERGING_SKILL")
    assert any(s["id"] == custom_text_id for s in signals)


def test_student_profile_and_skills_repository_lifecycle():
    user_id = f"usr-std-{uuid.uuid4().hex[:8]}"
    skill_uuid = str(uuid.uuid4())
    profile_payload = {
        "user_id": user_id,
        "full_name": "Radhika Sharma",
        "target_role": "Robotics Engineer",
        "skills": [
            {"skill_id": skill_uuid, "skill_name": "ROS2", "proficiency": "advanced"}
        ],
        "career_interests": ["Robotics", "Computer Vision"],
        "is_demo": False,
    }
    saved = upsert_student_profile(profile_payload)
    assert saved["user_id"] == user_id
    assert len(saved["skills"]) == 1

    fetched = get_student_profile(user_id)
    assert fetched is not None
    assert fetched["full_name"] == "Radhika Sharma"

    deleted = delete_student_profile(user_id)
    assert deleted is True
    assert get_student_profile(user_id) is None
