"""Read-only MCP resource definitions for SkillSetu."""
import asyncio
from typing import Any

from app.routers.schemes import get_scheme_metadata
from app.routers.opportunities import opportunities_summary
from app.routers.sync import get_sync_status


def _run_async(coro):
    """Run an async coroutine synchronously."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def resource_schemes_categories() -> dict[str, Any]:
    """Return available scheme categories, types, and eligible courses."""
    return _run_async(get_scheme_metadata())


def resource_opportunities_summary() -> dict[str, Any]:
    """Return aggregated count of opportunities by type and top districts."""
    return _run_async(opportunities_summary())


def resource_sync_status() -> dict[str, Any]:
    """Return pipeline health and approved data sources."""
    return _run_async(get_sync_status())


RESOURCES = {
    "skillsetu://schemes/categories": {
        "uri": "skillsetu://schemes/categories",
        "name": "Scheme Categories & Types",
        "description": "Available scheme beneficiary categories, scheme types, and eligible course types in SkillSetu.",
        "mimeType": "application/json",
        "handler": resource_schemes_categories,
    },
    "skillsetu://opportunities/summary": {
        "uri": "skillsetu://opportunities/summary",
        "name": "Opportunity Summary Breakdown",
        "description": "Total opportunity counts categorized by jobs, internships, apprenticeships, and top districts.",
        "mimeType": "application/json",
        "handler": resource_opportunities_summary,
    },
    "skillsetu://sync/status": {
        "uri": "skillsetu://sync/status",
        "name": "Data Pipeline Health & Status",
        "description": "Operational status, API key configuration state, and catalog of approved government data feeds.",
        "mimeType": "application/json",
        "handler": resource_sync_status,
    },
}
