-- SkillSetu Database Schema
-- Supabase PostgreSQL + pgvector ready
-- Run this in the Supabase SQL Editor after creating your project

-- Enable pgvector extension (uncomment when ready)
-- CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- USERS
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('government', 'institute', 'employer', 'student')),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- SKILLS (master taxonomy)
-- ============================================================
CREATE TABLE IF NOT EXISTS skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    nsqf_level INT CHECK (nsqf_level BETWEEN 1 AND 10),
    synonyms TEXT[] DEFAULT '{}',
    -- embedding VECTOR(384),  -- uncomment when pgvector RAG is activated
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- JOBS
-- ============================================================
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    district TEXT NOT NULL,
    industry TEXT NOT NULL,
    description TEXT,
    source TEXT DEFAULT 'DEMO_SYNTHETIC',
    source_label TEXT DEFAULT 'Demo Data',
    posted_date DATE DEFAULT CURRENT_DATE
);

-- ============================================================
-- JOB_SKILLS (many-to-many: jobs <-> skills)
-- ============================================================
CREATE TABLE IF NOT EXISTS job_skills (
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    skill_id UUID REFERENCES skills(id) ON DELETE CASCADE,
    proficiency_required TEXT CHECK (proficiency_required IN ('beginner', 'intermediate', 'advanced')),
    PRIMARY KEY (job_id, skill_id)
);

-- ============================================================
-- COURSES
-- ============================================================
CREATE TABLE IF NOT EXISTS courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    institute TEXT NOT NULL,
    district TEXT NOT NULL,
    description TEXT,
    enrolment_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- COURSE_SKILLS (many-to-many: courses <-> skills)
-- ============================================================
CREATE TABLE IF NOT EXISTS course_skills (
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    skill_id UUID REFERENCES skills(id) ON DELETE CASCADE,
    coverage_level INT CHECK (coverage_level BETWEEN 1 AND 5),
    PRIMARY KEY (course_id, skill_id)
);

-- ============================================================
-- PLACEMENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS placements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    year INT NOT NULL,
    student_count INT NOT NULL,
    placed_count INT NOT NULL
);

-- ============================================================
-- EMPLOYERS
-- ============================================================
CREATE TABLE IF NOT EXISTS employers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    industry TEXT NOT NULL,
    district TEXT NOT NULL
);

-- ============================================================
-- EMPLOYER_FEEDBACK (validation: confirm/correct/reject)
-- ============================================================
CREATE TABLE IF NOT EXISTS employer_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employer_id UUID REFERENCES employers(id) ON DELETE CASCADE,
    skill_id UUID REFERENCES skills(id) ON DELETE CASCADE,
    demand_level TEXT CHECK (demand_level IN ('low', 'medium', 'high', 'critical')),
    proficiency_required TEXT CHECK (proficiency_required IN ('beginner', 'intermediate', 'advanced')),
    status TEXT CHECK (status IN ('pending', 'confirmed', 'corrected', 'rejected')) DEFAULT 'pending',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- INDUSTRY_SIGNALS
-- ============================================================
CREATE TABLE IF NOT EXISTS industry_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    technology TEXT NOT NULL,
    summary TEXT NOT NULL,
    impact_level TEXT CHECK (impact_level IN ('low', 'medium', 'high', 'critical')) NOT NULL,
    signal_date DATE DEFAULT CURRENT_DATE
);

-- ============================================================
-- SIGNAL_SKILLS (many-to-many: signals <-> skills)
-- ============================================================
CREATE TABLE IF NOT EXISTS signal_skills (
    signal_id UUID REFERENCES industry_signals(id) ON DELETE CASCADE,
    skill_id UUID REFERENCES skills(id) ON DELETE CASCADE,
    impact_score INT CHECK (impact_score BETWEEN 1 AND 10),
    PRIMARY KEY (signal_id, skill_id)
);

-- ============================================================
-- SKILL_FORECASTS
-- ============================================================
CREATE TABLE IF NOT EXISTS skill_forecasts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_id UUID REFERENCES skills(id) ON DELETE CASCADE,
    period TEXT CHECK (period IN ('6m', '12m', '24m')) NOT NULL,
    current_demand TEXT CHECK (current_demand IN ('low', 'medium', 'high', 'very_high')),
    future_demand TEXT CHECK (future_demand IN ('low', 'medium', 'high', 'very_high')),
    trend TEXT CHECK (trend IN ('rising', 'stable', 'declining')) NOT NULL,
    confidence INT CHECK (confidence BETWEEN 0 AND 100),
    UNIQUE (skill_id, period)
);

-- ============================================================
-- STUDENT_PROFILES
-- ============================================================
CREATE TABLE IF NOT EXISTS student_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    target_role TEXT NOT NULL,
    skill_match_pct INT DEFAULT 0
);

-- ============================================================
-- STUDENT_SKILLS
-- ============================================================
CREATE TABLE IF NOT EXISTS student_skills (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    skill_id UUID REFERENCES skills(id) ON DELETE CASCADE,
    proficiency TEXT CHECK (proficiency IN ('beginner', 'intermediate', 'advanced')) NOT NULL,
    PRIMARY KEY (user_id, skill_id)
);

-- ============================================================
-- RECOMMENDATIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target_type TEXT CHECK (target_type IN ('course', 'district', 'student', 'curriculum')) NOT NULL,
    target_id TEXT,
    recommendation TEXT NOT NULL,
    reason TEXT NOT NULL,
    supporting_data JSONB DEFAULT '{}',
    confidence INT CHECK (confidence BETWEEN 0 AND 100),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- INDEXES for common queries
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_jobs_district ON jobs(district);
CREATE INDEX IF NOT EXISTS idx_jobs_industry ON jobs(industry);
CREATE INDEX IF NOT EXISTS idx_skills_category ON skills(category);
CREATE INDEX IF NOT EXISTS idx_employer_feedback_status ON employer_feedback(status);
CREATE INDEX IF NOT EXISTS idx_skill_forecasts_trend ON skill_forecasts(trend);
CREATE INDEX IF NOT EXISTS idx_recommendations_target_type ON recommendations(target_type);
