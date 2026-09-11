import asyncio
import datetime
import logging
import time
import uuid
from typing import Any

from app.config import settings
from app.core.data_mode import is_explicit_demo_mode
from app.db import get_demo
from app.ingestion.sync_engine import SyncEngine

logger = logging.getLogger("skillsetu.ingestion.scheduler")


class IngestionScheduler:

    def __init__(self, engine: SyncEngine | None = None):
        self.engine = engine or SyncEngine()
        self._lock: asyncio.Lock | None = None
        self._task: asyncio.Task | None = None
        self._stop_event: asyncio.Event | None = None
        self._is_sync_running = False
        self._last_run_timestamp: str | None = None
        self._last_attempted_run_timestamp: str | None = None
        self._last_successful_run_timestamp: str | None = None
        self._last_run_duration_ms: int = 0
        self._last_error: str | None = None

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def _get_stop_event(self) -> asyncio.Event:
        if self._stop_event is None:
            self._stop_event = asyncio.Event()
        return self._stop_event

    @property
    def is_active(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def is_sync_running(self) -> bool:
        return self._is_sync_running

    def start(self):
        if not settings.auto_sync_enabled:
            logger.info("Auto-sync is disabled via configuration (AUTO_SYNC_ENABLED=False).")
            return

        if self.is_active:
            logger.warning("IngestionScheduler is already running.")
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            self._stop_event = asyncio.Event()
            self._lock = asyncio.Lock()
            self._task = loop.create_task(self._worker_loop(), name="SkillSetu-SyncScheduler")
            logger.info(
                "IngestionScheduler started (interval=%d minutes, sync_on_startup=%s).",
                settings.effective_refresh_interval_minutes,
                settings.sync_on_startup,
            )
        else:
            logger.info("No active event loop found during scheduler.start(); skipping task creation.")

    async def stop(self):
        if not self.is_active:
            return

        logger.info("Stopping IngestionScheduler...")
        stop_event = self._get_stop_event()
        stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("IngestionScheduler stopped.")

    def _check_active_distributed_sync(self, lease_seconds: int = 900) -> bool:
        try:
            if is_explicit_demo_mode():
                logs = [l for l in get_demo("sync_logs") if l.get("is_demo") is True]
            else:
                from app.repositories.supabase_repository import list_sync_logs
                logs = list_sync_logs(limit=10)
                logs = [l for l in logs if not l.get("is_demo")]
            now_dt = datetime.datetime.now(datetime.timezone.utc)
            for log in logs:
                if log.get("status") == "running":
                    started_str = log.get("started_at")
                    if started_str:
                        started_dt = datetime.datetime.fromisoformat(started_str)
                        if (now_dt - started_dt).total_seconds() < lease_seconds:
                            return True
        except Exception as exc:
            logger.warning("Error checking active distributed sync: %s", exc)
            return False
        return False

    async def execute_sync(self, source: str = "data.gov.in") -> dict[str, Any]:
        lock = self._get_lock()
        if lock.locked() or self._is_sync_running:
            logger.warning("Synchronization requested while another sync is actively running. Skipping.")
            return {
                "status": "skipped",
                "message": "Synchronization is already in progress. Overlapping run prevented.",
            }

        async with lock:
            if self._is_sync_running:
                logger.warning("Synchronization requested while another sync is actively running. Skipping.")
                return {
                    "status": "skipped",
                    "message": "Synchronization is already in progress. Overlapping run prevented.",
                }

            loop = asyncio.get_running_loop()
            is_distributed_running = await loop.run_in_executor(None, self._check_active_distributed_sync)
            if is_distributed_running:
                logger.warning("Synchronization requested while another sync is actively running. Skipping.")
                return {
                    "status": "skipped",
                    "message": "Synchronization is already in progress. Overlapping run prevented.",
                }

            self._is_sync_running = True
            attempt_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
            start_perf = time.perf_counter()
            self._last_attempted_run_timestamp = attempt_time
            self._last_run_timestamp = attempt_time
            try:
                loop = asyncio.get_running_loop()

                if source in ("industry_signals", "industry"):
                    from app.ingestion.industry_intelligence import industry_ingestor
                    from app.db import save_sync_log
                    ind_res = await loop.run_in_executor(None, industry_ingestor.ingest_from_feeds)
                    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    self._last_successful_run_timestamp = now_str
                    self._last_error = None
                    self._last_run_duration_ms = int((time.perf_counter() - start_perf) * 1000)
                    fetched_cnt = ind_res.get("records_fetched", ind_res.get("fetched", 0))
                    added_cnt = ind_res.get("records_added", ind_res.get("added", 0))
                    updated_cnt = ind_res.get("records_updated", ind_res.get("updated", 0))
                    skipped_cnt = ind_res.get("records_duplicated", ind_res.get("skipped", 0))
                    save_sync_log({
                        "id": str(uuid.uuid4()),
                        "source_name": source,
                        "job_type": "scheduled_sync",
                        "status": "success",
                        "records_fetched": fetched_cnt,
                        "records_added": added_cnt,
                        "records_updated": updated_cnt,
                        "records_skipped": skipped_cnt,
                        "error_message": None,
                        "started_at": attempt_time,
                        "completed_at": now_str,
                        "duration_ms": self._last_run_duration_ms,
                        "sources_detail": {
                            "industry_signals": {
                                "status": "SUCCESS" if fetched_cnt > 0 else "NO_DATA",
                                "error": None,
                                "records_fetched": fetched_cnt,
                                "records_added": added_cnt,
                                "records_updated": updated_cnt,
                                "records_skipped": skipped_cnt,
                            }
                        },
                    })
                    return {"status": "success", "source": source, "industry_sync": ind_res, "duration_ms": self._last_run_duration_ms}

                if source in ("skill_forecasts", "forecasts", "forecast"):
                    from app.services.forecast_engine import persist_computed_forecasts
                    from app.db import save_sync_log
                    fc_res = await loop.run_in_executor(None, persist_computed_forecasts)
                    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    self._last_successful_run_timestamp = now_str
                    self._last_error = None
                    self._last_run_duration_ms = int((time.perf_counter() - start_perf) * 1000)
                    fc_cnt = len(fc_res)
                    save_sync_log({
                        "id": str(uuid.uuid4()),
                        "source_name": source,
                        "job_type": "scheduled_sync",
                        "status": "success",
                        "records_fetched": fc_cnt,
                        "records_added": fc_cnt,
                        "records_updated": 0,
                        "records_skipped": 0,
                        "error_message": None,
                        "started_at": attempt_time,
                        "completed_at": now_str,
                        "duration_ms": self._last_run_duration_ms,
                        "sources_detail": {
                            "skill_forecasts": {
                                "status": "SUCCESS" if fc_cnt > 0 else "NO_DATA",
                                "error": None,
                                "records_fetched": fc_cnt,
                                "records_added": fc_cnt,
                                "records_updated": 0,
                                "records_skipped": 0,
                            }
                        },
                    })
                    return {"status": "success", "source": source, "forecasts_persisted": len(fc_res), "duration_ms": self._last_run_duration_ms}

                result = await loop.run_in_executor(None, self.engine.run_sync, source)
                if source == "all":
                    from app.services.forecast_engine import persist_computed_forecasts
                    await loop.run_in_executor(None, persist_computed_forecasts)

                if "source" not in result:
                    result["source"] = source

                self._last_run_duration_ms = result.get("duration_ms", int((time.perf_counter() - start_perf) * 1000))
                if result.get("status") == "success":
                    self._last_successful_run_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    self._last_error = None
                else:
                    self._last_error = result.get("error_message") or "Sync run failed"
                return result
            except Exception as exc:
                self._last_error = str(exc)
                logger.exception("Error executing sync: %s", exc)
                return {
                    "status": "failed",
                    "source": source,
                    "error_message": str(exc),
                    "started_at": attempt_time,
                    "completed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                }
            finally:
                self._is_sync_running = False

    async def _worker_loop(self):
        try:
            loop = asyncio.get_running_loop()
            should_catchup = await loop.run_in_executor(None, self._should_catchup_sync)
            if settings.sync_on_startup or should_catchup:
                logger.info("Performing initial/catch-up data synchronization on startup...")
                await self.execute_sync(source=settings.sync_sources or "all")

            interval_seconds = max(settings.effective_refresh_interval_minutes * 60, 60)
            stop_event = self._get_stop_event()

            while not stop_event.is_set():
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
                    break
                except asyncio.TimeoutError:
                    logger.info("Scheduled sync interval elapsed. Triggering automated ingestion...")
                    try:
                        await self.execute_sync(source=settings.sync_sources or "all")
                    except Exception as exc:
                        logger.exception("Error during scheduled automated ingestion: %s", exc)

        except asyncio.CancelledError:
            logger.info("Scheduler worker loop cancelled.")
        except Exception as exc:
            logger.exception("Unexpected error in scheduler worker loop: %s", exc)

    def _should_catchup_sync(self) -> bool:
        if is_explicit_demo_mode():
            logs = [l for l in get_demo("sync_logs") if l.get("is_demo") is True]
        else:
            try:
                from app.repositories.supabase_repository import list_sync_logs
                logs = list_sync_logs(limit=10)
                logs = [l for l in logs if not l.get("is_demo")]
            except Exception as exc:
                logger.warning("Error fetching sync logs for catchup check: %s", exc)
                logs = []

        if not logs:
            return True

        logs.sort(key=lambda x: x.get("started_at", ""), reverse=True)
        last_log = logs[0]
        started_str = last_log.get("started_at")
        if not started_str:
            return True

        try:
            last_dt = datetime.datetime.fromisoformat(started_str)
            now_dt = datetime.datetime.now(datetime.timezone.utc)
            minutes_elapsed = (now_dt - last_dt).total_seconds() / 60
            return minutes_elapsed >= settings.effective_refresh_interval_minutes
        except Exception as exc:
            logger.warning("Error parsing timestamp for catchup check: %s", exc)
            return True

    def get_status(self) -> dict[str, Any]:
        return {
            "auto_sync_enabled": settings.auto_sync_enabled,
            "scheduler_active": self.is_active,
            "is_sync_running": self._is_sync_running,
            "interval_hours": settings.sync_interval_hours,
            "refresh_interval_minutes": settings.effective_refresh_interval_minutes,
            "interval_minutes": settings.effective_refresh_interval_minutes,
            "last_run_timestamp": self._last_run_timestamp,
            "last_attempted_run_timestamp": self._last_attempted_run_timestamp,
            "last_successful_run_timestamp": self._last_successful_run_timestamp,
            "last_run_duration_ms": self._last_run_duration_ms,
            "last_error": self._last_error,
        }


scheduler = IngestionScheduler()
