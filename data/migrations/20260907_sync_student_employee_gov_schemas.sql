DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'student_profiles' AND column_name = 'user_id' AND data_type = 'uuid'
    ) THEN
        ALTER TABLE student_profiles ALTER COLUMN user_id TYPE TEXT USING user_id::text;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS student_profiles (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    full_name TEXT,
    institution TEXT,
    degree TEXT,
    education_level TEXT,
    academic_year TEXT,
    graduation_year INT,
    target_role TEXT NOT NULL,
    desired_role TEXT,
    preferred_location TEXT,
    career_interests TEXT[] DEFAULT '{}',
    skills JSONB DEFAULT '[]'::jsonb,
    projects JSONB DEFAULT '[]'::jsonb,
    certifications JSONB DEFAULT '[]'::jsonb,
    courses JSONB DEFAULT '[]'::jsonb,
    skill_match_pct INT DEFAULT 0,
    source TEXT DEFAULT 'USER_SUBMITTED',
    is_demo BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS full_name TEXT;
ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS institution TEXT;
ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS degree TEXT;
ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS education_level TEXT;
ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS academic_year TEXT;
ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS graduation_year INT;
ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS desired_role TEXT;
ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS preferred_location TEXT;
ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS career_interests TEXT[] DEFAULT '{}';
ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS skills JSONB DEFAULT '[]'::jsonb;
ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS projects JSONB DEFAULT '[]'::jsonb;
ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS certifications JSONB DEFAULT '[]'::jsonb;
ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS courses JSONB DEFAULT '[]'::jsonb;
ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'USER_SUBMITTED';
ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS is_demo BOOLEAN DEFAULT FALSE;
ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now();
ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

CREATE TABLE IF NOT EXISTS employee_profiles (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    full_name TEXT,
    "current_role" TEXT NOT NULL,
    years_of_experience NUMERIC(4,1) DEFAULT 0,
    industry TEXT,
    education TEXT,
    target_role TEXT,
    preferred_location TEXT,
    skills JSONB DEFAULT '[]'::jsonb,
    certifications JSONB DEFAULT '[]'::jsonb,
    source TEXT DEFAULT 'USER_SUBMITTED',
    is_demo BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE employee_profiles ADD COLUMN IF NOT EXISTS full_name TEXT;
ALTER TABLE employee_profiles ADD COLUMN IF NOT EXISTS "current_role" TEXT;
ALTER TABLE employee_profiles ADD COLUMN IF NOT EXISTS years_of_experience NUMERIC(4,1) DEFAULT 0;
ALTER TABLE employee_profiles ADD COLUMN IF NOT EXISTS industry TEXT;
ALTER TABLE employee_profiles ADD COLUMN IF NOT EXISTS education TEXT;
ALTER TABLE employee_profiles ADD COLUMN IF NOT EXISTS target_role TEXT;
ALTER TABLE employee_profiles ADD COLUMN IF NOT EXISTS preferred_location TEXT;
ALTER TABLE employee_profiles ADD COLUMN IF NOT EXISTS skills JSONB DEFAULT '[]'::jsonb;
ALTER TABLE employee_profiles ADD COLUMN IF NOT EXISTS certifications JSONB DEFAULT '[]'::jsonb;
ALTER TABLE employee_profiles ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'USER_SUBMITTED';
ALTER TABLE employee_profiles ADD COLUMN IF NOT EXISTS is_demo BOOLEAN DEFAULT FALSE;
ALTER TABLE employee_profiles ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now();
ALTER TABLE employee_profiles ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

CREATE TABLE IF NOT EXISTS gov_opportunities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    department TEXT,
    description TEXT,
    eligibility_criteria TEXT,
    target_skills TEXT[] DEFAULT '{}',
    district_coverage TEXT[] DEFAULT '{}',
    opportunity_type TEXT DEFAULT 'APPRENTICESHIP',
    application_url TEXT,
    deadline TEXT,
    status TEXT DEFAULT 'active',
    source TEXT DEFAULT 'USER_SUBMITTED',
    data_provenance TEXT DEFAULT 'GOVERNMENT_OFFICIAL',
    is_demo BOOLEAN DEFAULT FALSE,
    user_id TEXT,
    user_email TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE gov_opportunities ADD COLUMN IF NOT EXISTS eligibility_criteria TEXT;
ALTER TABLE gov_opportunities ADD COLUMN IF NOT EXISTS target_skills TEXT[] DEFAULT '{}';
ALTER TABLE gov_opportunities ADD COLUMN IF NOT EXISTS district_coverage TEXT[] DEFAULT '{}';
ALTER TABLE gov_opportunities ADD COLUMN IF NOT EXISTS opportunity_type TEXT DEFAULT 'APPRENTICESHIP';
ALTER TABLE gov_opportunities ADD COLUMN IF NOT EXISTS application_url TEXT;
ALTER TABLE gov_opportunities ADD COLUMN IF NOT EXISTS deadline TEXT;
ALTER TABLE gov_opportunities ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active';
ALTER TABLE gov_opportunities ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'USER_SUBMITTED';
ALTER TABLE gov_opportunities ADD COLUMN IF NOT EXISTS data_provenance TEXT DEFAULT 'GOVERNMENT_OFFICIAL';
ALTER TABLE gov_opportunities ADD COLUMN IF NOT EXISTS is_demo BOOLEAN DEFAULT FALSE;
ALTER TABLE gov_opportunities ADD COLUMN IF NOT EXISTS user_id TEXT;
ALTER TABLE gov_opportunities ADD COLUMN IF NOT EXISTS user_email TEXT;
ALTER TABLE gov_opportunities ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now();
ALTER TABLE gov_opportunities ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

NOTIFY pgrst, 'reload schema';
