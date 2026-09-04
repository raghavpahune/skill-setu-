"""Synchronization Engine for SkillSetu.

Coordinates data ingestion from Tier-A external connectors:
1. data.gov.in (OGD Platform India: scholarships, CTS, NAPS, PMKVY)
2. Adzuna India Jobs API (live vacancies across Maharashtra districts)

Enforces SHA-256 deduplication, validates via Pydantic, stamps unforgeable provenance,
updates schemes and jobs in authoritative Supabase (and cache), and records audit trails.
"""
from __future__ import annotations

import datetime
import logging
import time
import uuid
from typing import Any

from app.db import (
    get_demo,
    set_demo,
    save_sync_log,
    persist_schemes_to_supabase,
    persist_jobs_to_supabase,
)
from app.ingestion.adzuna_connector import AdzunaConnector
from app.ingestion.datagov_connector import (
    DataGovConnector,
    RESOURCE_SCHOLARSHIP_ALLOCATION,
    RESOURCE_ITI_CRAFTSMEN,
    RESOURCE_NAPS_APPRENTICESHIP,
    RESOURCE_PMKVY_SKILL,
)

logger = logging.getLogger("skillsetu.ingestion.sync_engine")


class SyncEngine:
    """Orchestrates data fetching, deduplication, and sync logging."""

    def __init__(
        self,
        datagov_connector: DataGovConnector | None = None,
        adzuna_connector: AdzunaConnector | None = None,
    ):
        self.datagov_connector = datagov_connector or DataGovConnector()
        self.adzuna_connector = adzuna_connector or AdzunaConnector()
        # Keep self.connector alias for backwards compatibility
        self.connector = self.datagov_connector

    def run_sync(self, source_name: str = "all") -> dict[str, Any]:
        """Execute full automated ingestion and log the results into sync_logs."""
        sync_id = str(uuid.uuid4())
        started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        start_perf = time.perf_counter()

        log_entry: dict[str, Any] = {
            "id": sync_id,
            "source_name": source_name,
            "job_type": "automated_external_ingestion",
            "status": "running",
            "records_fetched": 0,
            "records_added": 0,
            "records_updated": 0,
            "records_skipped": 0,
            "error_message": None,
            "started_at": started_at,
            "completed_at": None,
            "duration_ms": 0,
        }
        save_sync_log(log_entry)

        try:
            total_fetched = 0
            total_added = 0
            total_updated = 0
            src_norm = (source_name or "all").lower().strip()

            # ----------------------------------------------------------------
            # 1. Ingest Schemes and Opportunities from data.gov.in
            # ----------------------------------------------------------------
            if src_norm in ("all", "data.gov.in", "schemes", "ogd"):
                logger.info("[SyncEngine] Ingesting government datasets from data.gov.in...")
                # Student Welfare Schemes
                raw_sch = self.datagov_connector.fetch_resource(RESOURCE_SCHOLARSHIP_ALLOCATION)
                sch_records = raw_sch.get("records", [])
                total_fetched += len(sch_records)
                transformed_schemes = self.datagov_connector.transform_scholarship_schemes(sch_records)

                # Craftsmen Training Schemes
                raw_cts = self.datagov_connector.fetch_resource(RESOURCE_ITI_CRAFTSMEN)
                cts_records = raw_cts.get("records", [])
                total_fetched += len(cts_records)
                transformed_schemes.extend(self.datagov_connector.transform_cts_schemes(cts_records))

                added_s, updated_s = self._upsert_schemes(transformed_schemes)
                total_added += added_s
                total_updated += updated_s

                # Government Apprenticeships (NAPS)
                raw_naps = self.datagov_connector.fetch_resource(RESOURCE_NAPS_APPRENTICESHIP)
                naps_records = raw_naps.get("records", [])
                total_fetched += len(naps_records)
                transformed_opps = self.datagov_connector.transform_naps_opportunities(naps_records)

                # PMKVY Vocational Training
                raw_pmkvy = self.datagov_connector.fetch_resource(RESOURCE_PMKVY_SKILL)
                pmkvy_records = raw_pmkvy.get("records", [])
                total_fetched += len(pmkvy_records)
                transformed_opps.extend(self.datagov_connector.transform_pmkvy_opportunities(pmkvy_records))

                added_o, updated_o = self._upsert_jobs(transformed_opps)
                total_added += added_o
                total_updated += updated_o

            # ----------------------------------------------------------------
            # 2. Ingest Live Jobs from Adzuna India API
            # ----------------------------------------------------------------
            if src_norm in ("all", "adzuna", "jobs"):
                logger.info("[SyncEngine] Ingesting live job vacancies from Adzuna India...")
                adzuna_raw = self.adzuna_connector.fetch_raw(page=1, results_per_page=25, where="Maharashtra")
                total_fetched += len(adzuna_raw)

                adzuna_jobs = self.adzuna_connector.validate_and_transform(adzuna_raw)
                added_j, updated_j = self._upsert_jobs(adzuna_jobs)
                total_added += added_j
                total_updated += updated_j

                # Ingest job-skill linkages
                self._upsert_job_skills(adzuna_jobs)

            # Compute execution timing
            duration_ms = int((time.perf_counter() - start_perf) * 1000)
            completed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

            # Update log entry
            log_entry.update({
                "status": "success",
                "records_fetched": total_fetched,
                "records_added": total_added,
                "records_updated": total_updated,
                "completed_at": completed_at,
                "duration_ms": duration_ms,
            })
            save_sync_log(log_entry)

            logger.info(
                "Sync completed successfully in %d ms: fetched=%d, added=%d, updated=%d",
                duration_ms, total_fetched, total_added, total_updated
            )
            return log_entry

        except Exception as exc:
            duration_ms = int((time.perf_counter() - start_perf) * 1000)
            completed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
            error_msg = str(exc)
            logger.exception("Ingestion failed: %s", error_msg)

            log_entry.update({
                "status": "failed",
                "error_message": error_msg,
                "completed_at": completed_at,
                "duration_ms": duration_ms,
            })
            save_sync_log(log_entry)
            return log_entry

    def _upsert_schemes(self, incoming_schemes: list[dict[str, Any]]) -> tuple[int, int]:
        """Deduplicate and upsert schemes by content_hash and (source, external_id)."""
        current_schemes = list(get_demo("schemes"))

        # Build index by content_hash and by (source, external_id)
        hash_index = {
            s.get("content_hash"): idx
            for idx, s in enumerate(current_schemes)
            if s.get("content_hash")
        }
        source_id_index = {
            (s.get("source"), s.get("external_id")): idx
            for idx, s in enumerate(current_schemes)
            if s.get("source") and s.get("external_id")
        }

        added = 0
        updated = 0
        now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

        for s in incoming_schemes:
            c_hash = s.get("content_hash")
            s_key = (s.get("source"), s.get("external_id"))

            target_idx = None
            if c_hash and c_hash in hash_index:
                target_idx = hash_index[c_hash]
            elif s_key in source_id_index:
                target_idx = source_id_index[s_key]

            if target_idx is not None:
                # Existing record: update last_seen_at and last_synced_at without inserting duplicate
                s["last_synced_at"] = now_ts
                s["last_seen_at"] = now_ts
                current_schemes[target_idx].update(s)
                updated += 1
            else:
                # New record
                s["last_synced_at"] = now_ts
                s["last_seen_at"] = now_ts
                current_schemes.append(s)
                new_idx = len(current_schemes) - 1
                if c_hash:
                    hash_index[c_hash] = new_idx
                source_id_index[s_key] = new_idx
                added += 1

        set_demo("schemes", current_schemes)

        # Authoritative persistence to Supabase repository
        try:
            from app.repositories.supabase_repository import upsert_schemes
            upsert_schemes(incoming_schemes)
        except Exception:
            persist_schemes_to_supabase(incoming_schemes)

        return added, updated

    def _upsert_jobs(self, incoming_jobs: list[dict[str, Any]]) -> tuple[int, int]:
        """Deduplicate and upsert jobs/opportunities by content_hash and (source, external_id)."""
        current_jobs = list(get_demo("jobs"))

        # Build index by content_hash and (source, external_id)
        hash_index = {
            j.get("content_hash"): idx
            for idx, j in enumerate(current_jobs)
            if j.get("content_hash")
        }
        source_id_index = {
            (j.get("source"), j.get("external_id")): idx
            for idx, j in enumerate(current_jobs)
            if j.get("source") and j.get("external_id")
        }

        added = 0
        updated = 0
        now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

        for job in incoming_jobs:
            c_hash = job.get("content_hash")
            j_key = (job.get("source"), job.get("external_id"))

            target_idx = None
            if c_hash and c_hash in hash_index:
                target_idx = hash_index[c_hash]
            elif j_key in source_id_index:
                target_idx = source_id_index[j_key]

            if target_idx is not None:
                # Update existing job timestamps
                job["last_synced_at"] = now_ts
                job["last_seen_at"] = now_ts
                current_jobs[target_idx].update(job)
                updated += 1
            else:
                # Add new job
                job["last_synced_at"] = now_ts
                job["last_seen_at"] = now_ts
                current_jobs.append(job)
                new_idx = len(current_jobs) - 1
                if c_hash:
                    hash_index[c_hash] = new_idx
                source_id_index[j_key] = new_idx
                added += 1

        set_demo("jobs", current_jobs)

        # Authoritative persistence to Supabase repository
        try:
            from app.repositories.supabase_repository import upsert_jobs
            upsert_jobs(incoming_jobs)
        except Exception:
            persist_jobs_to_supabase(incoming_jobs)

        return added, updated

    # Alias for backwards compatibility
    _upsert_opportunities = _upsert_jobs

    def _upsert_job_skills(self, jobs: list[dict[str, Any]]) -> int:
        """Extract and persist many-to-many job-skill mappings."""
        current_js = list(get_demo("job_skills"))
        existing_keys = {(js.get("job_id"), js.get("skill_id")) for js in current_js}

        new_links = []
        for job in jobs:
            jid = job.get("id")
            if not jid:
                continue
            for sid in job.get("skill_ids", []):
                if (jid, sid) not in existing_keys:
                    link = {
                        "job_id": jid,
                        "skill_id": sid,
                        "proficiency_required": "intermediate",
                    }
                    current_js.append(link)
                    existing_keys.add((jid, sid))
                    new_links.append(link)

        if new_links:
            set_demo("job_skills", current_js)
            try:
                from app.repositories.supabase_repository import batch_create_job_skills
                batch_create_job_skills(new_links)
            except Exception as e:
                logger.debug("[SyncEngine] Skipping Supabase batch_create_job_skills: %s", e)

        return len(new_links)
