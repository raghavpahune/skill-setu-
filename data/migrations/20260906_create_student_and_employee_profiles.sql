ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
ALTER TABLE users ADD CONSTRAINT users_role_check
CHECK (UPPER(role) IN ('GOVERNMENT', 'INSTITUTE', 'EMPLOYER', 'STUDENT', 'ADMIN', 'EMPLOYEE'));

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

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_employee_profiles_user'
    ) THEN
        ALTER TABLE employee_profiles
        ADD CONSTRAINT fk_employee_profiles_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_student_profiles_target_role ON student_profiles(target_role);
CREATE INDEX IF NOT EXISTS idx_student_profiles_preferred_location ON student_profiles(preferred_location);
CREATE INDEX IF NOT EXISTS idx_employee_profiles_target_role ON employee_profiles(target_role);
CREATE INDEX IF NOT EXISTS idx_employee_profiles_current_role ON employee_profiles("current_role");
CREATE INDEX IF NOT EXISTS idx_employee_profiles_industry ON employee_profiles(industry);
