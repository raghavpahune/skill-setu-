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
    target_role TEXT NOT NULL DEFAULT 'AI Engineer',
    desired_role TEXT,
    preferred_location TEXT,
    career_interests TEXT[] DEFAULT '{}',
    skills JSONB DEFAULT '[]'::jsonb,
    projects JSONB DEFAULT '[]'::jsonb,
    certifications JSONB DEFAULT '[]'::jsonb,
    courses JSONB DEFAULT '[]'::jsonb,
    experience JSONB DEFAULT '[]'::jsonb,
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
ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS experience JSONB DEFAULT '[]'::jsonb;
ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'USER_SUBMITTED';
ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS is_demo BOOLEAN DEFAULT FALSE;
ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now();
ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'student_skills' AND column_name = 'user_id' AND data_type = 'uuid'
    ) THEN
        ALTER TABLE student_skills ALTER COLUMN user_id TYPE TEXT USING user_id::text;
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'student_skills' AND column_name = 'skill_id' AND data_type = 'uuid'
    ) THEN
        ALTER TABLE student_skills ALTER COLUMN skill_id TYPE TEXT USING skill_id::text;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS student_skills (
    user_id TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    proficiency TEXT NOT NULL DEFAULT 'intermediate',
    PRIMARY KEY (user_id, skill_id)
);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'industry_signals' AND column_name = 'id' AND data_type = 'uuid'
    ) THEN
        ALTER TABLE industry_signals ALTER COLUMN id TYPE TEXT USING id::text;
    END IF;
END $$;

ALTER TABLE industry_signals ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE industry_signals ADD COLUMN IF NOT EXISTS category TEXT DEFAULT 'INDUSTRY_DEMAND';
ALTER TABLE industry_signals ADD COLUMN IF NOT EXISTS industry TEXT DEFAULT 'Cross-Sector Tech';
ALTER TABLE industry_signals ADD COLUMN IF NOT EXISTS skills TEXT[] DEFAULT '{}';
ALTER TABLE industry_signals ADD COLUMN IF NOT EXISTS tools TEXT[] DEFAULT '{}';
ALTER TABLE industry_signals ADD COLUMN IF NOT EXISTS source_url TEXT;
ALTER TABLE industry_signals ADD COLUMN IF NOT EXISTS source_name TEXT;
ALTER TABLE industry_signals ADD COLUMN IF NOT EXISTS source_type TEXT DEFAULT 'INDUSTRY_ANNOUNCEMENT';
ALTER TABLE industry_signals ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ DEFAULT now();
ALTER TABLE industry_signals ADD COLUMN IF NOT EXISTS collected_at TIMESTAMPTZ DEFAULT now();
ALTER TABLE industry_signals ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();
ALTER TABLE industry_signals ADD COLUMN IF NOT EXISTS validation_status TEXT DEFAULT 'APPROVED';
ALTER TABLE industry_signals ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE industry_signals ADD COLUMN IF NOT EXISTS is_demo BOOLEAN DEFAULT FALSE;
ALTER TABLE industry_signals ADD COLUMN IF NOT EXISTS data_provenance TEXT DEFAULT 'VERIFIED_EXTERNAL_FEED';
ALTER TABLE industry_signals ADD COLUMN IF NOT EXISTS freshness TEXT DEFAULT 'NEW';
ALTER TABLE industry_signals ADD COLUMN IF NOT EXISTS is_ai_processed BOOLEAN DEFAULT FALSE;
ALTER TABLE industry_signals ADD COLUMN IF NOT EXISTS ai_metadata JSONB;
ALTER TABLE industry_signals ADD COLUMN IF NOT EXISTS signature TEXT;
ALTER TABLE industry_signals ADD COLUMN IF NOT EXISTS admin_notes TEXT;

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE employee_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE employers ENABLE ROW LEVEL SECURITY;
ALTER TABLE employer_demands ENABLE ROW LEVEL SECURITY;
ALTER TABLE employer_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE courses ENABLE ROW LEVEL SECURITY;
ALTER TABLE course_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE placements ENABLE ROW LEVEL SECURITY;
ALTER TABLE industry_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE signal_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE skill_forecasts ENABLE ROW LEVEL SECURITY;
ALTER TABLE schemes ENABLE ROW LEVEL SECURITY;
ALTER TABLE gov_opportunities ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_logs ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    DROP POLICY IF EXISTS "service_role_all_users" ON users;
    DROP POLICY IF EXISTS "users_read_own_record" ON users;
    DROP POLICY IF EXISTS "deny_anon_users" ON users;

    DROP POLICY IF EXISTS "service_role_all_profiles" ON student_profiles;
    DROP POLICY IF EXISTS "students_read_own_profile" ON student_profiles;
    DROP POLICY IF EXISTS "students_modify_own_profile" ON student_profiles;
    DROP POLICY IF EXISTS "deny_anon_profiles" ON student_profiles;

    DROP POLICY IF EXISTS "service_role_all_student_skills" ON student_skills;
    DROP POLICY IF EXISTS "students_read_own_skills" ON student_skills;
    DROP POLICY IF EXISTS "students_modify_own_skills" ON student_skills;
    DROP POLICY IF EXISTS "deny_anon_student_skills" ON student_skills;

    DROP POLICY IF EXISTS "service_role_all_assessments" ON student_assessments;
    DROP POLICY IF EXISTS "students_read_own_assessments" ON student_assessments;
    DROP POLICY IF EXISTS "students_insert_own_assessments" ON student_assessments;
    DROP POLICY IF EXISTS "deny_anon_assessments" ON student_assessments;

    DROP POLICY IF EXISTS "service_role_all_employee_profiles" ON employee_profiles;
    DROP POLICY IF EXISTS "employees_manage_own_profile" ON employee_profiles;
    DROP POLICY IF EXISTS "deny_anon_employee_profiles" ON employee_profiles;

    DROP POLICY IF EXISTS "service_role_all_gov_opps" ON gov_opportunities;
    DROP POLICY IF EXISTS "public_read_gov_opportunities" ON gov_opportunities;
    DROP POLICY IF EXISTS "gov_modify_own_opportunities" ON gov_opportunities;

    DROP POLICY IF EXISTS "service_role_all_skills" ON skills;
    DROP POLICY IF EXISTS "public_read_skills" ON skills;

    DROP POLICY IF EXISTS "service_role_all_jobs" ON jobs;
    DROP POLICY IF EXISTS "public_read_jobs" ON jobs;

    DROP POLICY IF EXISTS "service_role_all_job_skills" ON job_skills;
    DROP POLICY IF EXISTS "public_read_job_skills" ON job_skills;

    DROP POLICY IF EXISTS "service_role_all_courses" ON courses;
    DROP POLICY IF EXISTS "public_read_courses" ON courses;

    DROP POLICY IF EXISTS "service_role_all_course_skills" ON course_skills;
    DROP POLICY IF EXISTS "public_read_course_skills" ON course_skills;

    DROP POLICY IF EXISTS "service_role_all_signals" ON industry_signals;
    DROP POLICY IF EXISTS "public_read_signals" ON industry_signals;

    DROP POLICY IF EXISTS "service_role_all_signal_skills" ON signal_skills;
    DROP POLICY IF EXISTS "public_read_signal_skills" ON signal_skills;

    DROP POLICY IF EXISTS "service_role_all_forecasts" ON skill_forecasts;
    DROP POLICY IF EXISTS "public_read_forecasts" ON skill_forecasts;

    DROP POLICY IF EXISTS "service_role_all_schemes" ON schemes;
    DROP POLICY IF EXISTS "public_read_schemes" ON schemes;

    DROP POLICY IF EXISTS "service_role_all_sync_logs" ON sync_logs;
    DROP POLICY IF EXISTS "deny_anon_sync_logs" ON sync_logs;
END $$;

CREATE POLICY "service_role_all_users" ON users FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "users_read_own_record" ON users FOR SELECT TO authenticated USING (auth.uid()::text = id);
CREATE POLICY "deny_anon_users" ON users FOR ALL TO anon USING (false);

CREATE POLICY "service_role_all_profiles" ON student_profiles FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "students_read_own_profile" ON student_profiles FOR SELECT TO authenticated USING (auth.uid()::text = user_id);
CREATE POLICY "students_modify_own_profile" ON student_profiles FOR ALL TO authenticated USING (auth.uid()::text = user_id) WITH CHECK (auth.uid()::text = user_id);
CREATE POLICY "deny_anon_profiles" ON student_profiles FOR ALL TO anon USING (false);

CREATE POLICY "service_role_all_student_skills" ON student_skills FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "students_read_own_skills" ON student_skills FOR SELECT TO authenticated USING (auth.uid()::text = user_id);
CREATE POLICY "students_modify_own_skills" ON student_skills FOR ALL TO authenticated USING (auth.uid()::text = user_id) WITH CHECK (auth.uid()::text = user_id);
CREATE POLICY "deny_anon_student_skills" ON student_skills FOR ALL TO anon USING (false);

CREATE POLICY "service_role_all_assessments" ON student_assessments FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "students_read_own_assessments" ON student_assessments FOR SELECT TO authenticated USING (auth.uid()::text = user_id OR auth.email() = user_email);
CREATE POLICY "students_insert_own_assessments" ON student_assessments FOR INSERT TO authenticated WITH CHECK (auth.uid()::text = user_id);
CREATE POLICY "deny_anon_assessments" ON student_assessments FOR ALL TO anon USING (false);

CREATE POLICY "service_role_all_employee_profiles" ON employee_profiles FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "employees_manage_own_profile" ON employee_profiles FOR ALL TO authenticated USING (auth.uid()::text = user_id) WITH CHECK (auth.uid()::text = user_id);
CREATE POLICY "deny_anon_employee_profiles" ON employee_profiles FOR ALL TO anon USING (false);

CREATE POLICY "service_role_all_gov_opps" ON gov_opportunities FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "public_read_gov_opportunities" ON gov_opportunities FOR SELECT TO public USING (true);
CREATE POLICY "gov_modify_own_opportunities" ON gov_opportunities FOR ALL TO authenticated USING (auth.uid()::text = user_id) WITH CHECK (auth.uid()::text = user_id);

CREATE POLICY "service_role_all_skills" ON skills FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "public_read_skills" ON skills FOR SELECT TO public USING (true);

CREATE POLICY "service_role_all_jobs" ON jobs FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "public_read_jobs" ON jobs FOR SELECT TO public USING (true);

CREATE POLICY "service_role_all_job_skills" ON job_skills FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "public_read_job_skills" ON job_skills FOR SELECT TO public USING (true);

CREATE POLICY "service_role_all_courses" ON courses FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "public_read_courses" ON courses FOR SELECT TO public USING (true);

CREATE POLICY "service_role_all_course_skills" ON course_skills FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "public_read_course_skills" ON course_skills FOR SELECT TO public USING (true);

CREATE POLICY "service_role_all_signals" ON industry_signals FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "public_read_signals" ON industry_signals FOR SELECT TO public USING (true);

CREATE POLICY "service_role_all_signal_skills" ON signal_skills FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "public_read_signal_skills" ON signal_skills FOR SELECT TO public USING (true);

CREATE POLICY "service_role_all_forecasts" ON skill_forecasts FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "public_read_forecasts" ON skill_forecasts FOR SELECT TO public USING (true);

CREATE POLICY "service_role_all_schemes" ON schemes FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "public_read_schemes" ON schemes FOR SELECT TO public USING (true);

CREATE POLICY "service_role_all_sync_logs" ON sync_logs FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "deny_anon_sync_logs" ON sync_logs FOR ALL TO anon USING (false);

NOTIFY pgrst, 'reload schema';
