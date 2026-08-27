"""Schemes API — student welfare and government schemes."""
from fastapi import APIRouter, HTTPException, Query
from app.db import get_demo

router = APIRouter()


@router.get("/schemes")
async def list_schemes(
    category: str | None = None,
    scheme_type: str | None = None,
    course_type: str | None = None,
    district: str | None = None,
    max_income: int | None = None,
    status: str | None = None,
    q: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List available student welfare, scholarship, and government schemes with optional filters."""
    schemes = get_demo("schemes")

    filtered = []
    for s in schemes:
        # Active status filter
        if status and s.get("status", "active").lower() != status.lower():
            continue

        # Beneficiary category filter (e.g. SC, ST, OBC, EWS, Women)
        if category:
            cat_upper = category.upper()
            cats = [c.upper() for c in s.get("beneficiary_category", [])]
            # Match if requested category is in beneficiary list, or if scheme is Open/All
            if cat_upper not in cats and "OPEN" not in cats and "ALL" not in cats:
                continue

        # Scheme type filter (e.g. scholarship, fee_waiver, hostel_allowance, stipend)
        if scheme_type and s.get("scheme_type", "").lower() != scheme_type.lower():
            continue

        # Eligible course type filter (e.g. ITI, Polytechnic, Diploma, Engineering)
        if course_type:
            ct_lower = course_type.lower()
            course_types = [c.lower() for c in s.get("eligible_course_types", [])]
            if ct_lower not in course_types:
                continue

        # District filter: if scheme specifies districts, check; otherwise it is state-wide
        if district:
            scheme_districts = s.get("districts")
            if scheme_districts and district.lower() not in [d.lower() for d in scheme_districts]:
                continue

        # Income ceiling filter (student eligible if family income <= scheme ceiling)
        if max_income is not None:
            ceiling = s.get("income_ceiling_annual")
            if ceiling is not None and ceiling < max_income:
                continue

        # Search query (title, department, benefit description)
        if q:
            q_lower = q.lower()
            text_corpus = f"{s.get('title', '')} {s.get('department', '')} {s.get('benefit_description', '')}".lower()
            if q_lower not in text_corpus:
                continue

        filtered.append(s)

    return filtered[offset : offset + limit]


@router.get("/schemes/categories")
async def get_scheme_metadata():
    """Return distinct categories, scheme types, and course types for UI filtering."""
    schemes = get_demo("schemes")
    categories = set()
    scheme_types = set()
    course_types = set()

    for s in schemes:
        for cat in s.get("beneficiary_category", []):
            categories.add(cat)
        if s.get("scheme_type"):
            scheme_types.add(s["scheme_type"])
        for ct in s.get("eligible_course_types", []):
            course_types.add(ct)

    return {
        "categories": sorted(list(categories)),
        "scheme_types": sorted(list(scheme_types)),
        "course_types": sorted(list(course_types)),
        "total_schemes": len(schemes),
    }


@router.get("/schemes/{scheme_id}")
async def get_scheme(scheme_id: str):
    """Get single scheme details by ID or scheme code."""
    schemes = get_demo("schemes")
    for s in schemes:
        if s.get("id") == scheme_id or s.get("scheme_code", "").lower() == scheme_id.lower():
            return s

    raise HTTPException(status_code=404, detail="Scheme not found")
