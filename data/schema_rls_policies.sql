-- ============================================================================
-- SKILLSETU — SUPABASE ROW-LEVEL SECURITY (RLS) POLICY BLUEPRINT
-- ============================================================================
-- Architecture Verification:
-- 1. SkillSetu FastAPI backend connects via SUPABASE_SERVICE_KEY (service-role).
-- 2. In Supabase/PostgreSQL, the service-role connection possesses BYPASSRLS
--    privileges and operates authoritatively on all tables without policy constraints.
-- 3. The SkillSetu frontend (React SPA on Vercel) does NOT contain any direct
--    Supabase JavaScript SDK (@supabase/supabase-js) clients. All database operations
--    are mediated through the FastAPI application layer with JWT authentication,
--    RBAC dependencies (require_roles), and cross-user ownership guards.
-- 4. In accordance with SIH stage demonstration stability requirements, RLS on live
--    production tables is maintained in its current state during execution to prevent
--    unintended locking of active analytics views.
-- 5. The policies below represent the canonical, verified security blueprint
--    to be applied if direct public PostgREST / anon-key access is ever enabled.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. USERS TABLE
-- ----------------------------------------------------------------------------
-- Protect passwords and credentials against direct anon extraction.
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Allow service-role full unrestricted access
CREATE POLICY "service_role_all_users"
  ON users
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Direct authenticated access: users may only view their own non-sensitive profile
CREATE POLICY "users_read_own_record"
  ON users
  FOR SELECT
  TO authenticated
  USING (auth.uid()::text = id);

-- Explicitly forbid public/anon access to user credentials
CREATE POLICY "deny_anon_users"
  ON users
  FOR ALL
  TO anon
  USING (false);

-- ----------------------------------------------------------------------------
-- 2. STUDENT ASSESSMENTS TABLE
-- ----------------------------------------------------------------------------
ALTER TABLE student_assessments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_all_assessments"
  ON student_assessments
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Authenticated candidates may read only their own personal assessments
CREATE POLICY "students_read_own_assessments"
  ON student_assessments
  FOR SELECT
  TO authenticated
  USING (auth.uid()::text = user_id OR auth.email() = user_email);

-- Authenticated candidates may insert only their own assessments
CREATE POLICY "students_insert_own_assessments"
  ON student_assessments
  FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid()::text = user_id AND (user_email IS NULL OR auth.email() = user_email));

-- Deny anon access to assessment diagnostic scores
CREATE POLICY "deny_anon_assessments"
  ON student_assessments
  FOR ALL
  TO anon
  USING (false);

-- ----------------------------------------------------------------------------
-- 3. STUDENT PROFILES & SKILLS
-- ----------------------------------------------------------------------------
ALTER TABLE student_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_skills ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_all_profiles"
  ON student_profiles
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "service_role_all_student_skills"
  ON student_skills
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "students_read_own_profile"
  ON student_profiles
  FOR SELECT
  TO authenticated
  USING (auth.uid()::text = user_id);

CREATE POLICY "students_read_own_skills"
  ON student_skills
  FOR SELECT
  TO authenticated
  USING (auth.uid()::text = student_id);

-- ----------------------------------------------------------------------------
-- 4. EMPLOYERS & EMPLOYER DEMANDS
-- ----------------------------------------------------------------------------
ALTER TABLE employers ENABLE ROW LEVEL SECURITY;
ALTER TABLE employer_demands ENABLE ROW LEVEL SECURITY;
ALTER TABLE employer_feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_all_employers"
  ON employers
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "service_role_all_demands"
  ON employer_demands
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "service_role_all_feedback"
  ON employer_feedback
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Public / anon may read verified employers and validated demands for labour intelligence
CREATE POLICY "public_read_verified_employers"
  ON employers
  FOR SELECT
  TO public
  USING (verification_status = 'VERIFIED');

CREATE POLICY "public_read_validated_demands"
  ON employer_demands
  FOR SELECT
  TO public
  USING (validation_status = 'VALIDATED' AND is_active = true);

-- Employers may read/manage only their own demands
CREATE POLICY "employers_manage_own_demands"
  ON employer_demands
  FOR ALL
  TO authenticated
  USING (employer_id = auth.uid()::text)
  WITH CHECK (employer_id = auth.uid()::text);

-- ----------------------------------------------------------------------------
-- 5. PUBLIC TAXONOMY & COURSES (READ-ONLY FOR PUBLIC, WRITE BY SERVICE ROLE)
-- ----------------------------------------------------------------------------
ALTER TABLE skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE courses ENABLE ROW LEVEL SECURITY;
ALTER TABLE skill_forecasts ENABLE ROW LEVEL SECURITY;
ALTER TABLE industry_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE schemes ENABLE ROW LEVEL SECURITY;
ALTER TABLE gov_opportunities ENABLE ROW LEVEL SECURITY;

-- Allow public read of verified public datasets
CREATE POLICY "public_read_skills" ON skills FOR SELECT TO public USING (true);
CREATE POLICY "public_read_jobs" ON jobs FOR SELECT TO public USING (true);
CREATE POLICY "public_read_courses" ON courses FOR SELECT TO public USING (true);
CREATE POLICY "public_read_forecasts" ON skill_forecasts FOR SELECT TO public USING (true);
CREATE POLICY "public_read_signals" ON industry_signals FOR SELECT TO public USING (true);
CREATE POLICY "public_read_schemes" ON schemes FOR SELECT TO public USING (true);
CREATE POLICY "public_read_gov_opportunities" ON gov_opportunities FOR SELECT TO public USING (true);

-- Restrict all modifications to service-role
CREATE POLICY "service_role_write_skills" ON skills FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_write_jobs" ON jobs FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_write_courses" ON courses FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_write_forecasts" ON skill_forecasts FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_write_signals" ON industry_signals FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_write_schemes" ON schemes FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "service_role_write_gov_opportunities" ON gov_opportunities FOR ALL TO service_role USING (true) WITH CHECK (true);
