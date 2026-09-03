"""Automatic background scheduler for SkillSetu data synchronization.

Runs periodic, non-blocking synchronization from official open data sources (data.gov.in)
using asyncio, with concurrency protection (asyncio.Lock), graceful shutdown,
and full audit logging in sync_logs.
"""
import asyncio
import datetime
import logging
from typing import Any

from app.config import settings
from app.db import get_demo
from app.ingestion.sync_engine import SyncEngine

logger = logging.getLogger("skillsetu.ingestion.scheduler")


class IngestionScheduler:
    """Manages periodic asynchronous data ingestion runs."""

    def __init__(self, engine: SyncEngine | None = None):
        self.engine = engine or SyncEngine()
        self._lock: asyncio.Lock | None = None
        self._task: asyncio.Task | None = None
        self._stop_event: asyncio.Event | None = None
        self._is_sync_running = False
        self._last_run_timestamp: str | None = None

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
        """Return True if background scheduler loop is running."""
        return self._task is not None and not self._task.done()

    @property
    def is_sync_running(self) -> bool:
        """Return True if an actual sync operation is actively in progress."""
        return self._is_sync_running

    def start(self):
        """Start the background scheduler loop if auto-sync is enabled."""
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
                "IngestionScheduler started (interval=%d hours, sync_on_startup=%s).",
                settings.sync_interval_hours,
                settings.sync_on_startup,
            )
        else:
            logger.info("No active event loop found during scheduler.start(); skipping task creation.")

    async def stop(self):
        """Stop the background scheduler loop gracefully."""
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

    async def execute_sync(self, source: str = "data.gov.in") -> dict[str, Any]:
        """Execute a synchronization run with strict concurrency/overlap protection.

        Can be invoked by both the background timer and manual API triggers.
        Guarantees that only ONE sync can execute at any time.
        """
        lock = self._get_lock()
        if lock.locked() or self._is_sync_running:
            logger.warning("Synchronization requested while another sync is actively running. Skipping.")
            return {
                "status": "skipped",
                "message": "Synchronization is already in progress. Overlapping run prevented.",
            }

        async with lock:
            self._is_sync_running = True
            try:
                # Run the sync engine (in thread executor to prevent blocking async event loop)
                loop = asyncio.get_running_loop()
                if source in ("industry_signals", "industry", "all"):
                    from app.ingestion.industry_intelligence import industry_ingestor
                    ind_res = await loop.run_in_executor(None, industry_ingestor.ingest_from_feeds)
                    if source != "all":
                        self._last_run_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
                        return {"status": "success", "source": source, "industry_sync": ind_res}

                if source in ("skill_forecasts", "forecasts", "forecast"):
                    from app.services.forecast_engine import persist_computed_forecasts
                    fc_res = await loop.run_in_executor(None, persist_computed_forecasts)
                    self._last_run_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    return {"status": "success", "source": source, "forecasts_persisted": len(fc_res)}

                result = await loop.run_in_executor(None, self.engine.run_sync, source)
                if source == "all":
                    from app.services.forecast_engine import persist_computed_forecasts
                    await loop.run_in_executor(None, persist_computed_forecasts)
                self._last_run_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
                return result

            finally:
                self._is_sync_running = False

    async def _worker_loop(self):
        """Background loop that periodically executes synchronization."""
        try:
            # 1. Startup check: sync if configured or if no previous sync exists
            if settings.sync_on_startup or self._should_catchup_sync():
                logger.info("Performing initial/catch-up data synchronization on startup...")
                await self.execute_sync()

            # 2. Main periodic loop
            interval_seconds = max(settings.sync_interval_hours * 3600, 60)
            stop_event = self._get_stop_event()

            while not stop_event.is_set():
                try:
                    # Wait for the interval or until stop event is signaled
                    await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
                    break  # Stop event was set
                except asyncio.TimeoutError:
                    # Interval elapsed — trigger scheduled synchronization
                    logger.info("Scheduled sync interval elapsed. Triggering automated ingestion...")
                    await self.execute_sync()

        except asyncio.CancelledError:
            logger.info("Scheduler worker loop cancelled.")
        except Exception as exc:
            logger.exception("Unexpected error in scheduler worker loop: %s", exc)

    def _should_catchup_sync(self) -> bool:
        """Check whether sufficient time has elapsed since the last recorded sync."""
        logs = list(get_demo("sync_logs"))
        if not logs:
            return True

        logs.sort(key=lambda x: x.get("started_at", ""), reverse=True)
        last_log = logs[0]
        started_str = last_log.get("started_at")
        if not started_str:
            return False

        try:
            last_dt = datetime.datetime.fromisoformat(started_str)
            now_dt = datetime.datetime.now(datetime.timezone.utc)
            hours_elapsed = (now_dt - last_dt).total_seconds() / 3600
            return hours_elapsed >= settings.sync_interval_hours
        except Exception:
            return False

    def get_status(self) -> dict[str, Any]:
        """Return operational state of the scheduler."""
        return {
            "auto_sync_enabled": settings.auto_sync_enabled,
            "scheduler_active": self.is_active,
            "is_sync_running": self._is_sync_running,
            "interval_hours": settings.sync_interval_hours,
            "last_run_timestamp": self._last_run_timestamp,
        }


# Global singleton instance
scheduler = IngestionScheduler()
