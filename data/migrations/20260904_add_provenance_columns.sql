-- ============================================================================
-- Migration: 20260904_add_provenance_columns.sql
-- Description: Idempotent migration adding explicit source classification,
--              historical snapshot preservation, and provenance tracking
--              columns and performance indexes to `jobs` and `schemes`.
-- Safety: Local only. DO NOT execute against remote Supabase production yet.
--         Safe to execute in Supabase SQL Editor after PR #3 merges.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. JOBS TABLE: Provenance, Source Classification & Snapshot Columns
-- ----------------------------------------------------------------------------

-- External unique identifier from source provider
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS external_id TEXT;

-- Explicit source classification (LIVE_API, VERIFIED_SNAPSHOT, SANDBOX_SIMULATION, DEMO_SYNTHETIC)
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS source_type TEXT DEFAULT 'DEMO_SYNTHETIC';

-- Human-readable provenance label (e.g., "Adzuna India Live API Feed", "Historical Maharashtra Job Snapshot")
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS source_label TEXT;

-- External dataset/resource identifier (e.g. data.gov.in resource UUID)
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS resource_id TEXT;

-- Provider publication date (when the job was originally posted by the employer/portal)
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ;

-- Actual snapshot capture date (strictly preserves capture timestamp for snapshots; never overwrites with now())
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS snapshot_captured_at TIMESTAMPTZ;

-- Timestamp when the record was last seen in an ingestion run
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ DEFAULT now();

-- Flag indicating whether the record is from a historical or static snapshot
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS is_snapshot BOOLEAN DEFAULT FALSE;

-- Captured unmapped technical keywords not yet in master taxonomy (stored as JSON array)
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS unmapped_skills JSONB DEFAULT '[]'::jsonb;

-- Base provenance fields (idempotent fallback if not present)
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS content_hash TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS source_url TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS fetched_at TIMESTAMPTZ DEFAULT now();
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS verification_status TEXT DEFAULT 'UNVERIFIED';
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS verification_method TEXT DEFAULT 'STRUCTURAL_API_VALIDATION';
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS confidence INT DEFAULT 0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS freshness_status TEXT DEFAULT 'UNKNOWN';
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS is_demo BOOLEAN DEFAULT TRUE;

-- Backfill pre-existing rows only when provenance fields are missing
UPDATE jobs
   SET source_type = COALESCE(source_type, CASE
           WHEN source = 'DEMO_SYNTHETIC' THEN 'DEMO_SYNTHETIC'
           WHEN source = 'SANDBOX_SIMULATION' THEN 'SANDBOX_SIMULATION'
           WHEN source = 'VERIFIED_SNAPSHOT' THEN 'VERIFIED_SNAPSHOT'
           WHEN source IN ('ADZUNA_API', 'DATAGOV_IN', 'OGD_DATAGOV_IN', 'LIVE_API') THEN 'LIVE_API'
           ELSE NULL
       END),
       verification_status = COALESCE(verification_status, CASE
           WHEN source IN ('DEMO_SYNTHETIC', 'SANDBOX_SIMULATION') THEN 'UNVERIFIED'
           WHEN source IN ('VERIFIED_SNAPSHOT', 'ADZUNA_API', 'DATAGOV_IN', 'OGD_DATAGOV_IN', 'LIVE_API') THEN 'VERIFIED'
           ELSE NULL
       END),
       confidence = COALESCE(confidence, CASE
           WHEN source IN ('DEMO_SYNTHETIC', 'SANDBOX_SIMULATION') THEN 0
           WHEN source = 'VERIFIED_SNAPSHOT' THEN 85
           WHEN source IN ('ADZUNA_API', 'DATAGOV_IN', 'OGD_DATAGOV_IN', 'LIVE_API') THEN 90
           ELSE NULL
       END),
       is_demo = COALESCE(is_demo, CASE
           WHEN source IN ('DEMO_SYNTHETIC', 'SANDBOX_SIMULATION') THEN TRUE
           WHEN source IN ('VERIFIED_SNAPSHOT', 'ADZUNA_API', 'DATAGOV_IN', 'OGD_DATAGOV_IN', 'LIVE_API') THEN FALSE
           ELSE NULL
       END)
 WHERE source_type IS NULL OR verification_status IS NULL OR confidence IS NULL OR is_demo IS NULL;


-- ----------------------------------------------------------------------------
-- 2. SCHEMES TABLE: Provenance, Source Classification & Snapshot Columns
-- ----------------------------------------------------------------------------

-- External unique identifier from source provider
ALTER TABLE schemes ADD COLUMN IF NOT EXISTS external_id TEXT;

-- Explicit source classification (LIVE_API, VERIFIED_SNAPSHOT, SANDBOX_SIMULATION, DEMO_SYNTHETIC)
ALTER TABLE schemes ADD COLUMN IF NOT EXISTS source_type TEXT DEFAULT 'DEMO_SYNTHETIC';

-- Human-readable provenance label (e.g., "data.gov.in Official Open Data Feed")
ALTER TABLE schemes ADD COLUMN IF NOT EXISTS source_label TEXT;

-- Government catalog resource identifier (e.g. bf44869a-519f-43cd-84f0-4914e32a37a8)
ALTER TABLE schemes ADD COLUMN IF NOT EXISTS resource_id TEXT;

-- Provider publication date
ALTER TABLE schemes ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ;

-- Snapshot capture timestamp for offline sandbox fixtures
ALTER TABLE schemes ADD COLUMN IF NOT EXISTS snapshot_captured_at TIMESTAMPTZ;

-- Timestamp when the scheme was last seen in an ingestion sync
ALTER TABLE schemes ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ DEFAULT now();

-- Flag indicating whether the record is from an offline snapshot or simulation
ALTER TABLE schemes ADD COLUMN IF NOT EXISTS is_snapshot BOOLEAN DEFAULT FALSE;

-- Base provenance fields (idempotent fallback if not present)
ALTER TABLE schemes ADD COLUMN IF NOT EXISTS content_hash TEXT;
ALTER TABLE schemes ADD COLUMN IF NOT EXISTS source_url TEXT;
ALTER TABLE schemes ADD COLUMN IF NOT EXISTS fetched_at TIMESTAMPTZ DEFAULT now();
ALTER TABLE schemes ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ;
ALTER TABLE schemes ADD COLUMN IF NOT EXISTS verification_status TEXT DEFAULT 'UNVERIFIED';
ALTER TABLE schemes ADD COLUMN IF NOT EXISTS verification_method TEXT DEFAULT 'GOVERNMENT_PORTAL_API_FEED';
ALTER TABLE schemes ADD COLUMN IF NOT EXISTS confidence INT DEFAULT 0;
ALTER TABLE schemes ADD COLUMN IF NOT EXISTS freshness_status TEXT DEFAULT 'UNKNOWN';
ALTER TABLE schemes ADD COLUMN IF NOT EXISTS is_demo BOOLEAN DEFAULT TRUE;

-- Backfill pre-existing rows only when provenance fields are missing
UPDATE schemes
   SET source_type = COALESCE(source_type, CASE
           WHEN source = 'DEMO_SYNTHETIC' THEN 'DEMO_SYNTHETIC'
           WHEN source = 'SANDBOX_SIMULATION' THEN 'SANDBOX_SIMULATION'
           WHEN source = 'VERIFIED_SNAPSHOT' THEN 'VERIFIED_SNAPSHOT'
           WHEN source IN ('DATAGOV_IN', 'OGD_DATAGOV_IN', 'LIVE_API') THEN 'LIVE_API'
           ELSE NULL
       END),
       verification_status = COALESCE(verification_status, CASE
           WHEN source IN ('DEMO_SYNTHETIC', 'SANDBOX_SIMULATION') THEN 'UNVERIFIED'
           WHEN source IN ('VERIFIED_SNAPSHOT', 'DATAGOV_IN', 'OGD_DATAGOV_IN', 'LIVE_API') THEN 'VERIFIED'
           ELSE NULL
       END),
       confidence = COALESCE(confidence, CASE
           WHEN source IN ('DEMO_SYNTHETIC', 'SANDBOX_SIMULATION') THEN 0
           WHEN source = 'VERIFIED_SNAPSHOT' THEN 90
           WHEN source IN ('DATAGOV_IN', 'OGD_DATAGOV_IN', 'LIVE_API') THEN 95
           ELSE NULL
       END),
       is_demo = COALESCE(is_demo, CASE
           WHEN source IN ('DEMO_SYNTHETIC', 'SANDBOX_SIMULATION') THEN TRUE
           WHEN source IN ('VERIFIED_SNAPSHOT', 'DATAGOV_IN', 'OGD_DATAGOV_IN', 'LIVE_API') THEN FALSE
           ELSE NULL
       END)
 WHERE source_type IS NULL OR verification_status IS NULL OR confidence IS NULL OR is_demo IS NULL;


-- ----------------------------------------------------------------------------
-- 3. INDEXES & CONSTRAINTS FOR DEDUPLICATION & QUERY PERFORMANCE
-- ----------------------------------------------------------------------------

-- Deduplication index on (source, external_id) to support ON CONFLICT upsert
-- Note: schemes table uniqueness is already enforced via schema constraint UNIQUE (source, external_id)
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_jobs_source_external_id ON jobs(source, external_id);

-- Fast content hash lookup index for deduplication across ingestion runs
CREATE INDEX IF NOT EXISTS idx_jobs_content_hash ON jobs(content_hash) WHERE content_hash IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_schemes_content_hash ON schemes(content_hash) WHERE content_hash IS NOT NULL;

-- Source type filtering index (distinguish LIVE_API vs VERIFIED_SNAPSHOT vs SANDBOX)
CREATE INDEX IF NOT EXISTS idx_jobs_source_type ON jobs(source_type);
CREATE INDEX IF NOT EXISTS idx_schemes_source_type ON schemes(source_type);

-- Partial index for high-velocity queries fetching only live, authentic vacancies
CREATE INDEX IF NOT EXISTS idx_jobs_live_active ON jobs(district, industry) WHERE is_demo = FALSE AND is_snapshot = FALSE;

-- Freshness status index for periodic cache invalidation and stale record pruning
CREATE INDEX IF NOT EXISTS idx_jobs_freshness ON jobs(freshness_status);
CREATE INDEX IF NOT EXISTS idx_schemes_freshness ON schemes(freshness_status);
