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

from app.config import settings
from app.core.data_mode import is_explicit_demo_mode
from app.db import (
    get_demo,
    set_demo,
    save_sync_log,
    is_supabase_connected,
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

    def __init__(
        self,
        datagov_connector: DataGovConnector | None = None,
        adzuna_connector: AdzunaConnector | None = None,
    ):
        self.datagov_connector = datagov_connector or DataGovConnector()
        self.adzuna_connector = adzuna_connector or AdzunaConnector()
        self.connector = self.datagov_connector

    def run_sync(self, source_name: str = "all") -> dict[str, Any]:
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
            total_skipped = 0
            src_norm = (source_name or "all").lower().strip()
            valid_sources = {
                "all",
                "data.gov.in",
                "schemes",
                "ogd",
                "adzuna",
                "jobs",
                "industry_signals",
                "industry",
                "skill_forecasts",
                "forecasts",
                "forecast",
            }
            if src_norm not in valid_sources:
                raise ValueError(f"Unsupported sync source selector '{source_name}'. Supported selectors: {sorted(valid_sources)}")

            source_errors = []
            source_successes = []

            if src_norm in ("all", "data.gov.in", "schemes", "ogd"):
                try:
                    logger.info("[SyncEngine] Ingesting government datasets from data.gov.in...")
                    raw_sch = self.datagov_connector.fetch_resource(RESOURCE_SCHOLARSHIP_ALLOCATION)
                    sch_records = raw_sch.get("records", [])
                    total_fetched += len(sch_records)
                    transformed_schemes = self.datagov_connector.transform_scholarship_schemes(sch_records)
                    total_skipped += max(0, len(sch_records) - len(transformed_schemes))

                    raw_cts = self.datagov_connector.fetch_resource(RESOURCE_ITI_CRAFTSMEN)
                    cts_records = raw_cts.get("records", [])
                    total_fetched += len(cts_records)
                    cts_schemes = self.datagov_connector.transform_cts_schemes(cts_records)
                    total_skipped += max(0, len(cts_records) - len(cts_schemes))
                    transformed_schemes.extend(cts_schemes)

                    added_s, updated_s = self._upsert_schemes(transformed_schemes)
                    total_added += added_s
                    total_updated += updated_s

                    raw_naps = self.datagov_connector.fetch_resource(RESOURCE_NAPS_APPRENTICESHIP)
                    naps_records = raw_naps.get("records", [])
                    total_fetched += len(naps_records)
                    transformed_opps = self.datagov_connector.transform_naps_opportunities(naps_records)
                    total_skipped += max(0, len(naps_records) - len(transformed_opps))

                    raw_pmkvy = self.datagov_connector.fetch_resource(RESOURCE_PMKVY_SKILL)
                    pmkvy_records = raw_pmkvy.get("records", [])
                    total_fetched += len(pmkvy_records)
                    pmkvy_opps = self.datagov_connector.transform_pmkvy_opportunities(pmkvy_records)
                    total_skipped += max(0, len(pmkvy_records) - len(pmkvy_opps))
                    transformed_opps.extend(pmkvy_opps)

                    added_o, updated_o = self._upsert_jobs(transformed_opps)
                    total_added += added_o
                    total_updated += updated_o
                    source_successes.append("data.gov.in")
                except Exception as err:
                    logger.warning("[SyncEngine] Datagov ingestion failed: %s", err)
                    source_errors.append(f"data.gov.in: {err}")

            if src_norm in ("all", "adzuna", "jobs"):
                try:
                    logger.info("[SyncEngine] Ingesting live job vacancies from Adzuna India...")
                    adzuna_raw = self.adzuna_connector.fetch_raw(page=1, results_per_page=25, where="Maharashtra")
                    total_fetched += len(adzuna_raw)

                    adzuna_jobs = self.adzuna_connector.validate_and_transform(adzuna_raw)
                    total_skipped += max(0, len(adzuna_raw) - len(adzuna_jobs))
                    added_j, updated_j = self._upsert_jobs(adzuna_jobs)
                    total_added += added_j
                    total_updated += updated_j

                    self._upsert_job_skills(adzuna_jobs)
                    source_successes.append("adzuna")
                except Exception as err:
                    logger.warning("[SyncEngine] Adzuna ingestion failed: %s", err)
                    source_errors.append(f"adzuna: {err}")

            if src_norm in ("all", "industry_signals", "industry"):
                try:
                    from app.ingestion.industry_intelligence import industry_ingestor
                    ind_res = industry_ingestor.ingest_from_feeds()
                    total_fetched += ind_res.get("fetched", 0)
                    total_added += ind_res.get("added", 0)
                    total_updated += ind_res.get("updated", 0)
                    total_skipped += ind_res.get("skipped", 0)
                    source_successes.append("industry_signals")
                except Exception as err:
                    logger.warning("[SyncEngine] Industry signals ingestion failed: %s", err)
                    source_errors.append(f"industry_signals: {err}")

            if src_norm in ("all", "skill_forecasts", "forecasts", "forecast"):
                try:
                    from app.services.forecast_engine import persist_computed_forecasts
                    fc_res = persist_computed_forecasts()
                    total_added += len(fc_res)
                    source_successes.append("skill_forecasts")
                except Exception as err:
                    logger.warning("[SyncEngine] Forecasts persistence failed: %s", err)
                    source_errors.append(f"skill_forecasts: {err}")

            duration_ms = int((time.perf_counter() - start_perf) * 1000)
            completed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

            if source_errors:
                if not source_successes:
                    status_val = "failed"
                else:
                    status_val = "partial" if src_norm == "all" else "failed"
                err_msg = "; ".join(source_errors)
            else:
                status_val = "success"
                err_msg = None

            log_entry.update({
                "status": status_val,
                "records_fetched": total_fetched,
                "records_added": total_added,
                "records_updated": total_updated,
                "records_skipped": total_skipped,
                "error_message": err_msg,
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
        is_demo = is_explicit_demo_mode()
        supabase_ready = is_supabase_connected()

        if is_demo:
            persisted_schemes = list(get_demo("schemes"))
        elif supabase_ready:
            from app.repositories.supabase_repository import list_schemes
            persisted_schemes = []
            page_size = 1000
            offset = 0
            while True:
                batch = list_schemes(limit=page_size, offset=offset) or []
                persisted_schemes.extend(batch)
                if len(batch) < page_size:
                    break
                offset += page_size
        elif not settings.use_demo_data:
            from app.repositories.supabase_repository import SupabaseConnectionError
            raise SupabaseConnectionError("Supabase connection required for real-mode sync")
        else:
            persisted_schemes = list(get_demo("schemes"))

        source_id_index = {
            (s.get("source"), s.get("external_id")): s
            for s in persisted_schemes
            if s.get("source") and s.get("external_id")
        }
        hash_index = {
            s.get("content_hash"): s
            for s in persisted_schemes
            if s.get("content_hash")
        }

        added = 0
        updated = 0
        now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

        for s in incoming_schemes:
            source = s.get("source")
            ext_id = s.get("external_id")
            c_hash = s.get("content_hash")

            target_record = None
            if source and ext_id:
                target_record = source_id_index.get((source, ext_id))
            elif c_hash:
                target_record = hash_index.get(c_hash)

            if target_record is not None:
                s["id"] = target_record.get("id") or s.get("id") or str(uuid.uuid4())
                s["last_synced_at"] = now_ts
                s["last_seen_at"] = now_ts
                target_record.update(s)
                updated += 1
            else:
                s["id"] = s.get("id") or str(uuid.uuid4())
                s["last_synced_at"] = now_ts
                s["last_seen_at"] = now_ts
                persisted_schemes.append(s)
                if source and ext_id:
                    source_id_index[(source, ext_id)] = s
                if c_hash:
                    hash_index[c_hash] = s
                added += 1

        if supabase_ready and not is_demo:
            from app.repositories.supabase_repository import upsert_schemes
            upsert_schemes(incoming_schemes)
        else:
            set_demo("schemes", persisted_schemes)

        return added, updated

    def _upsert_jobs(self, incoming_jobs: list[dict[str, Any]]) -> tuple[int, int]:
        is_demo = is_explicit_demo_mode()
        supabase_ready = is_supabase_connected()

        if is_demo:
            persisted_jobs = list(get_demo("jobs"))
        elif supabase_ready:
            from app.repositories.supabase_repository import list_jobs
            persisted_jobs = []
            page_size = 1000
            offset = 0
            while True:
                batch = list_jobs(limit=page_size, offset=offset) or []
                persisted_jobs.extend(batch)
                if len(batch) < page_size:
                    break
                offset += page_size
        elif not settings.use_demo_data:
            from app.repositories.supabase_repository import SupabaseConnectionError
            raise SupabaseConnectionError("Supabase connection required for real-mode sync")
        else:
            persisted_jobs = list(get_demo("jobs"))

        source_id_index = {
            (j.get("source"), (j.get("external_id") or j.get("ext_id"))): j
            for j in persisted_jobs
            if j.get("source") and (j.get("external_id") or j.get("ext_id"))
        }
        hash_index = {
            j.get("content_hash"): j
            for j in persisted_jobs
            if j.get("content_hash")
        }

        added = 0
        updated = 0
        now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

        for job in incoming_jobs:
            c_hash = job.get("content_hash")
            source = job.get("source")
            ext_id = job.get("external_id") or job.get("ext_id")
            if ext_id and not job.get("external_id"):
                job["external_id"] = ext_id

            target_record = None
            if source and ext_id:
                target_record = source_id_index.get((source, ext_id))
            elif c_hash:
                target_record = hash_index.get(c_hash)

            if target_record is not None:
                job["id"] = target_record.get("id") or job.get("id") or str(uuid.uuid4())
                job["last_synced_at"] = now_ts
                job["last_seen_at"] = now_ts
                target_record.update(job)
                updated += 1
            else:
                job["id"] = job.get("id") or str(uuid.uuid4())
                job["last_synced_at"] = now_ts
                job["last_seen_at"] = now_ts
                persisted_jobs.append(job)
                if source and ext_id:
                    source_id_index[(source, ext_id)] = job
                if c_hash:
                    hash_index[c_hash] = job
                added += 1

        if supabase_ready and not is_demo:
            from app.repositories.supabase_repository import upsert_jobs
            upsert_jobs(incoming_jobs)
        else:
            set_demo("jobs", persisted_jobs)

        return added, updated

    _upsert_opportunities = _upsert_jobs

    def _upsert_job_skills(self, jobs: list[dict[str, Any]]) -> int:
        is_demo = is_explicit_demo_mode()
        supabase_ready = is_supabase_connected()
        incoming_job_ids = [j.get("id") for j in jobs if j.get("id")]

        if is_demo:
            current_js = list(get_demo("job_skills"))
            existing_keys = {(js.get("job_id"), js.get("skill_id")) for js in current_js}
        elif supabase_ready:
            from app.repositories.supabase_repository import list_job_skills
            current_js = list_job_skills(job_ids=incoming_job_ids) or []
            existing_keys = {(js.get("job_id"), js.get("skill_id")) for js in current_js}
        elif not settings.use_demo_data:
            from app.repositories.supabase_repository import SupabaseConnectionError
            raise SupabaseConnectionError("Supabase connection required for real-mode sync")
        else:
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
                    existing_keys.add((jid, sid))
                    new_links.append(link)

        if new_links:
            if supabase_ready and not is_demo:
                from app.repositories.supabase_repository import batch_create_job_skills
                batch_create_job_skills(new_links)
            else:
                demo_js = list(get_demo("job_skills"))
                demo_js.extend(new_links)
                set_demo("job_skills", demo_js)

        return len(new_links)
