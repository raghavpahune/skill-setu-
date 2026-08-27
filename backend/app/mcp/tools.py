"""Read-only MCP tool definitions for SkillSetu."""
import asyncio
import json
from typing import Any

from app.db import get_demo
from app.routers.schemes import list_schemes
from app.routers.opportunities import list_opportunities
from app.services.gap_engine import compute_gaps


def _run_async(coro):
    """Run an async coroutine synchronously."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # In an already running loop, create a task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def tool_get_schemes(args: dict[str, Any]) -> dict[str, Any]:
    """Retrieve matching government welfare schemes, scholarships, and training grants."""
    category = args.get("category")
    scheme_type = args.get("scheme_type")
    course_type = args.get("course_type")
    district = args.get("district")
    max_income = args.get("max_income")
    q = args.get("q")
    limit = min(int(args.get("limit", 20)), 50)

    schemes = _run_async(list_schemes(
        category=category,
        scheme_type=scheme_type,
        course_type=course_type,
        district=district,
        max_income=max_income,
        status="active",
        q=q,
        limit=limit,
        offset=0,
    ))
    return {"total_returned": len(schemes), "schemes": schemes}


def tool_get_opportunities(args: dict[str, Any]) -> dict[str, Any]:
    """Retrieve jobs, internships, apprenticeships, and vocational training postings."""
    opportunity_type = args.get("opportunity_type")
    district = args.get("district")
    industry = args.get("industry")
    skill = args.get("skill")
    min_stipend = args.get("min_stipend")
    q = args.get("q")
    limit = min(int(args.get("limit", 20)), 50)

    opps = _run_async(list_opportunities(
        opportunity_type=opportunity_type,
        district=district,
        industry=industry,
        skill=skill,
        min_stipend=min_stipend,
        status="active",
        q=q,
        limit=limit,
        offset=0,
    ))
    return {"total_returned": len(opps), "opportunities": opps}


def tool_get_skill_gaps(args: dict[str, Any]) -> dict[str, Any]:
    """Calculate labour-market skill demand vs. supply gaps across industries and districts."""
    limit = min(int(args.get("limit", 10)), 25)
    gaps = compute_gaps()
    return {"total_gaps_calculated": len(gaps), "top_gaps": gaps[:limit]}


def tool_get_sync_freshness(args: dict[str, Any]) -> dict[str, Any]:
    """Retrieve the audit status, last sync timestamp, and freshness of external datasets."""
    logs = list(get_demo("sync_logs"))
    logs.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    last_log = logs[0] if logs else None

    # Safe summary with zero secrets exposed
    return {
        "status": "healthy" if last_log and last_log.get("status") == "success" else "idle",
        "total_sync_runs": len(logs),
        "last_sync_timestamp": last_log.get("completed_at") if last_log else None,
        "last_records_fetched": last_log.get("records_fetched", 0) if last_log else 0,
        "last_records_added": last_log.get("records_added", 0) if last_log else 0,
        "last_records_updated": last_log.get("records_updated", 0) if last_log else 0,
        "active_sources": ["data.gov.in"],
    }


# Tool Registry with MCP-compliant JSON Schemas
TOOLS = {
    "get_schemes": {
        "name": "get_schemes",
        "description": "Query government welfare schemes, scholarships, fee waivers, hostel grants, and training subsidies with multi-parameter filtering.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Target beneficiary category: SC, ST, OBC, EWS, Women, or Open",
                },
                "scheme_type": {
                    "type": "string",
                    "description": "Type of scheme: scholarship, fee_waiver, hostel_allowance, training_scheme, stipend, or tool_grant",
                },
                "course_type": {
                    "type": "string",
                    "description": "Eligible course type: ITI, Polytechnic, Diploma, or Engineering",
                },
                "district": {
                    "type": "string",
                    "description": "Maharashtra district name (e.g. Pune, Mumbai, Nagpur)",
                },
                "max_income": {
                    "type": "integer",
                    "description": "Annual family income in INR (filters schemes where ceiling is applicable)",
                },
                "q": {
                    "type": "string",
                    "description": "Search keywords matching title, department, or description",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum records to return (default 20, max 50)",
                },
            },
        },
        "handler": tool_get_schemes,
    },
    "get_opportunities": {
        "name": "get_opportunities",
        "description": "Query opportunities including full-time jobs, apprenticeships (NAPS), internships, and vocational training (PMKVY) with attached skill requirements.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "opportunity_type": {
                    "type": "string",
                    "enum": ["job", "internship", "apprenticeship", "vocational_training"],
                    "description": "Type of opportunity to filter by",
                },
                "district": {
                    "type": "string",
                    "description": "Target Maharashtra district (e.g. Pune, Mumbai, Nashik)",
                },
                "industry": {
                    "type": "string",
                    "description": "Industry sector (e.g. Manufacturing, Electric Vehicles, IT/ITES)",
                },
                "skill": {
                    "type": "string",
                    "description": "Required skill name or skill ID (e.g. Python, CNC Programming, PLC)",
                },
                "min_stipend": {
                    "type": "integer",
                    "description": "Minimum monthly stipend in INR",
                },
                "q": {
                    "type": "string",
                    "description": "Text search matching title, company, or description",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum records to return (default 20, max 50)",
                },
            },
        },
        "handler": tool_get_opportunities,
    },
    "get_skill_gaps": {
        "name": "get_skill_gaps",
        "description": "Compute and rank current labour-market skill demand vs. supply deficits, urgency rankings, and shortages for curriculum and career planning.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "district": {
                    "type": "string",
                    "description": "District to compute gaps for (omit for state-wide)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of top skill gaps to return (default 10, max 25)",
                },
            },
        },
        "handler": tool_get_skill_gaps,
    },
    "get_sync_freshness": {
        "name": "get_sync_freshness",
        "description": "Check the health, freshness, and audit history of external data sources (e.g. data.gov.in ingestion runs).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Source name to check (default: data.gov.in)",
                },
            },
        },
        "handler": tool_get_sync_freshness,
    },
}
