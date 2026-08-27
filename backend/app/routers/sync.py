"""Sync API — management and monitoring of automated data ingestion."""
from fastapi import APIRouter, Query
from app.db import get_demo
from app.ingestion.datagov_connector import (
    DataGovConnector,
    RESOURCE_SCHOLARSHIP_ALLOCATION,
    RESOURCE_ITI_CRAFTSMEN,
    RESOURCE_NAPS_APPRENTICESHIP,
    RESOURCE_NAPS_NATS_STIPEND,
    RESOURCE_PMKVY_SKILL,
)
from app.ingestion.sync_engine import SyncEngine

router = APIRouter()


@router.post("/sync/trigger")
async def trigger_sync(source: str = Query("data.gov.in", description="Source to ingest data from")):
    """Trigger an on-demand automated ingestion run and record execution in sync_logs."""
    connector = DataGovConnector()
    engine = SyncEngine(connector=connector)
    result = engine.run_sync(source_name=source)
    return result


@router.get("/sync/logs")
async def get_sync_logs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Retrieve audit history of automated sync operations."""
    logs = list(get_demo("sync_logs"))
    # Return sorted with most recent first
    logs.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    return logs[offset : offset + limit]


@router.get("/sync/status")
async def get_sync_status():
    """Return health, configuration state, and overview of the automated ingestion pipeline."""
    connector = DataGovConnector()
    logs = list(get_demo("sync_logs"))
    logs.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    last_run = logs[0] if logs else None

    return {
        "status": "healthy",
        "api_key_configured": connector.has_api_key,
        "total_sync_runs": len(logs),
        "last_sync": last_run,
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
