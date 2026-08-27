"""Synchronization Engine for SkillSetu.

Coordinates data ingestion from external connectors (e.g. data.gov.in),
enforces deduplication via (source, external_id), updates existing schemes and jobs,
and records comprehensive audit trails into sync_logs.
"""
import datetime
import logging
import time
import uuid
from typing import Any

from app.db import get_demo, set_demo, append_demo
from app.ingestion.datagov_connector import (
    DataGovConnector,
    RESOURCE_SCHOLARSHIP_ALLOCATION,
    RESOURCE_ITI_CRAFTSMEN,
    RESOURCE_NAPS_APPRENTICESHIP,
    RESOURCE_PMKVY_SKILL,
)

logger = logging.getLogger(__name__)


class SyncEngine:
    """Orchestrates data fetching, deduplication, and sync logging."""

    def __init__(self, connector: DataGovConnector | None = None):
        self.connector = connector or DataGovConnector()

    def run_sync(self, source_name: str = "data.gov.in") -> dict[str, Any]:
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
        append_demo("sync_logs", log_entry)

        try:
            total_fetched = 0
            total_added = 0
            total_updated = 0

            # ----------------------------------------------------------------
            # 1. Ingest Student Welfare Schemes
            # ----------------------------------------------------------------
            raw_sch = self.connector.fetch_resource(RESOURCE_SCHOLARSHIP_ALLOCATION)
            sch_records = raw_sch.get("records", [])
            total_fetched += len(sch_records)
            transformed_schemes = self.connector.transform_scholarship_schemes(sch_records)

            raw_cts = self.connector.fetch_resource(RESOURCE_ITI_CRAFTSMEN)
            cts_records = raw_cts.get("records", [])
            total_fetched += len(cts_records)
            transformed_schemes.extend(self.connector.transform_cts_schemes(cts_records))

            added_s, updated_s = self._upsert_schemes(transformed_schemes)
            total_added += added_s
            total_updated += updated_s

            # ----------------------------------------------------------------
            # 2. Ingest Opportunities (Apprenticeships & Vocational Training)
            # ----------------------------------------------------------------
            raw_naps = self.connector.fetch_resource(RESOURCE_NAPS_APPRENTICESHIP)
            naps_records = raw_naps.get("records", [])
            total_fetched += len(naps_records)
            transformed_opps = self.connector.transform_naps_opportunities(naps_records)

            raw_pmkvy = self.connector.fetch_resource(RESOURCE_PMKVY_SKILL)
            pmkvy_records = raw_pmkvy.get("records", [])
            total_fetched += len(pmkvy_records)
            transformed_opps.extend(self.connector.transform_pmkvy_opportunities(pmkvy_records))

            added_o, updated_o = self._upsert_opportunities(transformed_opps)
            total_added += added_o
            total_updated += updated_o

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
            return log_entry

    def _upsert_schemes(self, incoming_schemes: list[dict]) -> tuple[int, int]:
        """Deduplicate and upsert schemes by (source, external_id)."""
        current_schemes = list(get_demo("schemes"))
        # Map by (source, external_id)
        existing_index = {
            (s.get("source"), s.get("external_id")): idx
            for idx, s in enumerate(current_schemes)
            if s.get("source") and s.get("external_id")
        }

        added = 0
        updated = 0
        now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

        for s in incoming_schemes:
            key = (s.get("source"), s.get("external_id"))
            if key in existing_index:
                # Update existing scheme
                target_idx = existing_index[key]
                s["last_synced_at"] = now_ts
                current_schemes[target_idx].update(s)
                updated += 1
            else:
                # Add new scheme
                s["last_synced_at"] = now_ts
                current_schemes.append(s)
                existing_index[key] = len(current_schemes) - 1
                added += 1

        set_demo("schemes", current_schemes)
        return added, updated

    def _upsert_opportunities(self, incoming_opps: list[dict]) -> tuple[int, int]:
        """Deduplicate and upsert opportunities in jobs table by (source, external_id)."""
        current_jobs = list(get_demo("jobs"))
        existing_index = {
            (j.get("source"), j.get("external_id")): idx
            for idx, j in enumerate(current_jobs)
            if j.get("source") and j.get("external_id")
        }

        added = 0
        updated = 0
        now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

        for opp in incoming_opps:
            key = (opp.get("source"), opp.get("external_id"))
            if key in existing_index:
                # Update existing opportunity
                target_idx = existing_index[key]
                opp["last_synced_at"] = now_ts
                current_jobs[target_idx].update(opp)
                updated += 1
            else:
                # Add new opportunity
                opp["last_synced_at"] = now_ts
                current_jobs.append(opp)
                existing_index[key] = len(current_jobs) - 1
                added += 1

        set_demo("jobs", current_jobs)
        return added, updated
