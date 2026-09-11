import logging
from typing import Any
from fastapi import APIRouter, Header, HTTPException, Query, status, Depends

logger = logging.getLogger(__name__)
from app.config import settings
from app.core.data_mode import is_explicit_demo_mode
from app.db import get_demo
from app.ingestion.datagov_connector import (
    DataGovConnector,
    RESOURCE_SCHOLARSHIP_ALLOCATION,
    RESOURCE_ITI_CRAFTSMEN,
    RESOURCE_NAPS_APPRENTICESHIP,
    RESOURCE_NAPS_NATS_STIPEND,
    RESOURCE_PMKVY_SKILL,
)
from app.ingestion.adzuna_connector import AdzunaConnector
from app.ingestion.sync_engine import SyncEngine
from app.ingestion.scheduler import scheduler

from app.core.security import get_optional_current_user

router = APIRouter()


ALLOWED_SOURCES = {
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


@router.post("/sync/trigger")
async def trigger_sync(
    source: str = Query("data.gov.in", description="Source to ingest data from"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
    current_user: Any = Depends(get_optional_current_user),
):
    source_norm = (source or "data.gov.in").lower().strip()
    if source_norm not in ALLOWED_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sync source selector '{source}'. Allowed sources: {sorted(ALLOWED_SOURCES)}",
        )

    if settings.admin_api_key and settings.admin_api_key.strip():
        is_admin_user = current_user and (current_user.get("role") or "").upper() == "ADMIN"
        is_key_match = x_admin_key and x_admin_key.strip() == settings.admin_api_key.strip()
        if not is_admin_user and not is_key_match:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized: invalid or missing admin credentials",
            )

    result = await scheduler.execute_sync(source=source_norm)
    return result


@router.get("/sync/logs")
async def get_sync_logs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    is_demo: bool | None = Query(None, description="Explicit demo/real mode selector"),
):
    if is_explicit_demo_mode(is_demo):
        logs = list(get_demo("sync_logs"))
    else:
        try:
            from app.repositories.supabase_repository import list_sync_logs
            logs = list_sync_logs(limit=limit + offset)
        except Exception as e:
            logger.warning("[Sync] Failed fetching sync_logs from repository: %s", e)
            logs = []
    logs.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    return logs[offset : offset + limit]


@router.get("/sync/status")
async def get_sync_status(
    is_demo: bool | None = Query(None, description="Explicit demo/real mode selector"),
):
    dg_connector = DataGovConnector()
    adz_connector = AdzunaConnector()
    if is_explicit_demo_mode(is_demo):
        logs = list(get_demo("sync_logs"))
    else:
        try:
            from app.repositories.supabase_repository import list_sync_logs
            logs = list_sync_logs(limit=20)
        except Exception as e:
            logger.warning("[Sync] Failed fetching sync_logs from repository: %s", e)
            logs = []
    logs.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    last_run = logs[0] if logs else None
    last_success = next((l for l in logs if l.get("status") == "success"), None)

    last_details = (last_run.get("sources_detail") or {}) if last_run else {}
    dg_detail = last_details.get("data.gov.in") or {}
    dg_configured = dg_connector.has_api_key
    adz_detail = last_details.get("adzuna") or {}
    adz_configured = adz_connector.has_credentials
    ind_detail = last_details.get("industry_signals") or {}
    fc_detail = last_details.get("skill_forecasts") or {}

    sources_summary = {
        "data.gov.in": {
            "source": "data.gov.in",
            "status": dg_detail.get("status") or ("SUCCESS" if dg_configured else "NOT_CONFIGURED"),
            "configured": dg_configured,
            "last_sync": last_run.get("completed_at") if last_run else None,
            "records_fetched": dg_detail.get("records_fetched", 0),
            "records_added": dg_detail.get("records_added", 0),
            "records_updated": dg_detail.get("records_updated", 0),
            "records_skipped": dg_detail.get("records_skipped", 0),
            "error": dg_detail.get("error") or (None if dg_configured else "DATA_GOV_API_KEY is not configured in production environment."),
        },
        "adzuna": {
            "source": "adzuna",
            "status": adz_detail.get("status") or ("SUCCESS" if adz_configured else "NOT_CONFIGURED"),
            "configured": adz_configured,
            "last_sync": last_run.get("completed_at") if last_run else None,
            "records_fetched": adz_detail.get("records_fetched", 0),
            "records_added": adz_detail.get("records_added", 0),
            "records_updated": adz_detail.get("records_updated", 0),
            "records_skipped": adz_detail.get("records_skipped", 0),
            "error": adz_detail.get("error") or (None if adz_configured else "ADZUNA_APP_ID / ADZUNA_APP_KEY not configured in production environment."),
        },
        "industry_signals": {
            "source": "industry_signals",
            "status": ind_detail.get("status", "IDLE"),
            "configured": True,
            "last_sync": last_run.get("completed_at") if last_run else None,
            "records_fetched": ind_detail.get("records_fetched", 0),
            "records_added": ind_detail.get("records_added", 0),
            "records_updated": ind_detail.get("records_updated", 0),
            "records_skipped": ind_detail.get("records_skipped", 0),
            "error": ind_detail.get("error"),
        },
        "skill_forecasts": {
            "source": "skill_forecasts",
            "status": fc_detail.get("status", "IDLE"),
            "configured": True,
            "last_sync": last_run.get("completed_at") if last_run else None,
            "records_fetched": fc_detail.get("records_fetched", 0),
            "records_added": fc_detail.get("records_added", 0),
            "records_updated": fc_detail.get("records_updated", 0),
            "records_skipped": fc_detail.get("records_skipped", 0),
            "error": fc_detail.get("error"),
        },
    }

    return {
        "status": "healthy",
        "api_key_configured": dg_configured,
        "adzuna_configured": adz_configured,
        "sources": sources_summary,
        "scheduler": scheduler.get_status(),
        "refresh_interval_minutes": settings.effective_refresh_interval_minutes,
        "total_sync_runs": len(logs),
        "last_sync": last_run,
        "last_successful_sync": last_success,
        "approved_datasets": [
            {
                "resource_id": RESOURCE_SCHOLARSHIP_ALLOCATION,
                "title": "Allocation under Pre-Matric, Post-Matric & MCM Scholarship Schemes",
                "target_entity": "schemes",
            },
            {
                "resource_id": RESOURCE_ITI_CRAFTSMEN,
                "title": "Craftsmen Training Scheme (CTS) through ITIs",
                "target_entity": "schemes",
            },
            {
                "resource_id": RESOURCE_NAPS_APPRENTICESHIP,
                "title": "District-wise Apprentices Engaged under NAPS",
                "target_entity": "jobs (apprenticeship)",
            },
            {
                "resource_id": RESOURCE_NAPS_NATS_STIPEND,
                "title": "Stipend Disbursal Benchmark under NAPS & NATS",
                "target_entity": "jobs (stipend)",
            },
            {
                "resource_id": RESOURCE_PMKVY_SKILL,
                "title": "Candidates Enrolled & Placed under PMKVY",
                "target_entity": "jobs (vocational_training)",
            },
        ],
    }
