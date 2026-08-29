"""Government Opportunities API — apprenticeships, training programs, employment, and entrepreneurship schemes."""
from fastapi import APIRouter, HTTPException, Query
from app.db import get_demo

router = APIRouter()


def _match_student_to_opportunities(opportunities: list[dict], profile: dict) -> list[dict]:
    """Score and rank government opportunities against a student profile or assessment record.

    Returns opportunities sorted by relevance with match_reasons explaining why each matches.
    """
    student_skills = set()
    for s in profile.get("skills", []) + profile.get("current_skills", []):
        if isinstance(s, dict):
            sname = s.get("skill_name") or s.get("name")
            if sname:
                student_skills.add(str(sname).lower())
            sid = s.get("skill_id")
            if sid:
                student_skills.add(str(sid).lower())
        elif s:
            student_skills.add(str(s).lower())


    student_district = (profile.get("district") or "").lower()
    student_career = (profile.get("target_role") or profile.get("career_goal") or "").lower()
    student_education = (profile.get("education") or "").lower()

    # Interests from assessment records
    student_interests = {i.lower() for i in profile.get("interests", []) if i}

    scored = []
    for opp in opportunities:
        if opp.get("status", "active").lower() != "active":
            continue

        score = 0
        reasons = []

        # Skill match
        opp_skills = {s.lower() for s in (opp.get("target_skills") or [])}
        matched_skills = student_skills & opp_skills
        if matched_skills:
            score += len(matched_skills) * 3
            reasons.append(f"Matches skills: {', '.join(sorted(matched_skills)[:3])}")

        # Interest match
        matched_interests = student_interests & opp_skills
        if matched_interests:
            score += len(matched_interests) * 2
            reasons.append(f"Aligns with interests: {', '.join(sorted(matched_interests)[:3])}")

        # District match
        opp_coverage = opp.get("district_coverage", "")
        if isinstance(opp_coverage, list):
            opp_districts = {d.lower() for d in opp_coverage}
        else:
            opp_districts = {opp_coverage.lower()} if opp_coverage else set()

        if student_district:
            if student_district in opp_districts:
                score += 5
                reasons.append(f"Available in your district ({student_district.title()})")
            elif any("state-wide" in d for d in opp_districts):
                score += 3
                reasons.append("Available state-wide in Maharashtra")

        # Career goal / education match (text overlap)
        opp_text = f"{opp.get('name', '')} {opp.get('description', '')}".lower()
        if student_career and any(word in opp_text for word in student_career.split() if len(word) > 3):
            score += 2
            reasons.append(f"Related to career goal: {student_career.title()}")

        if student_education:
            edu_keywords = [w for w in student_education.split() if len(w) > 2]
            if any(kw.lower() in opp_text for kw in edu_keywords):
                score += 1
                reasons.append("Matches education background")

        if score > 0:
            scored.append({
                **opp,
                "relevance_score": score,
                "match_reasons": reasons,
            })

    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    return scored


@router.get("/gov/opportunities")
async def list_gov_opportunities(
    district: str | None = None,
    domain: str | None = None,
    skill: str | None = None,
    opportunity_type: str | None = None,
    status: str | None = None,
    q: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List government opportunities with optional filtering."""
    records = get_demo("gov_opportunities")

    filtered = []
    for r in records:
        # Status filter
        if status and r.get("status", "active").lower() != status.lower():
            continue

        # District filter
        if district:
            d_lower = district.lower()
            coverage = r.get("district_coverage", "")
            if isinstance(coverage, list):
                districts = [d.lower() for d in coverage]
            else:
                districts = [coverage.lower()] if coverage else []
            if d_lower not in districts and not any("state-wide" in d for d in districts):
                continue

        # Domain / skill filter
        if domain or skill:
            target = {s.lower() for s in (r.get("target_skills") or [])}
            if domain and domain.lower() not in target:
                continue
            if skill and skill.lower() not in target:
                continue

        # Opportunity type filter
        if opportunity_type and r.get("opportunity_type", "").lower() != opportunity_type.lower():
            continue

        # Search query
        if q:
            q_lower = q.lower()
            corpus = f"{r.get('name', '')} {r.get('department', '')} {r.get('description', '')} {' '.join(r.get('target_skills', []))}".lower()
            if q_lower not in corpus:
                continue

        filtered.append(r)

    return filtered[offset: offset + limit]


@router.get("/gov/opportunities/types")
async def gov_opportunity_types():
    """Return distinct opportunity types and districts for UI filtering."""
    records = get_demo("gov_opportunities")
    types = set()
    districts = set()
    skills = set()
    for r in records:
        if r.get("opportunity_type"):
            types.add(r["opportunity_type"])
        coverage = r.get("district_coverage", "")
        if isinstance(coverage, list):
            districts.update(coverage)
        elif coverage:
            districts.add(coverage)
        for s in r.get("target_skills", []):
            skills.add(s)

    return {
        "opportunity_types": sorted(types),
        "districts": sorted(districts),
        "skills": sorted(skills),
        "total": len(records),
    }


@router.get("/gov/opportunities/recommended/{student_id}")
async def recommended_gov_opportunities(
    student_id: str,
    limit: int = Query(10, ge=1, le=50),
):
    """Return government opportunities ranked by relevance to a student profile or assessment."""
    # Try student profiles first, then assessments
    profiles = get_demo("student_profiles")
    profile = None
    for p in profiles:
        if p.get("user_id") == student_id:
            profile = p
            break

    if not profile:
        assessments = get_demo("student_assessments")
        for a in assessments:
            if a.get("id") == student_id:
                profile = a
                break

    if not profile:
        raise HTTPException(status_code=404, detail=f"Student profile '{student_id}' not found.")

    opportunities = get_demo("gov_opportunities")
    ranked = _match_student_to_opportunities(opportunities, profile)

    return {
        "student_id": student_id,
        "total_matches": len(ranked),
        "opportunities": ranked[:limit],
        "provenance_note": "Recommendations are based on skill/district/interest overlap with demo dataset. Verify eligibility on official portals before applying.",
    }


@router.get("/gov/opportunities/{opp_id}")
async def get_gov_opportunity(opp_id: str):
    """Get individual government opportunity by ID."""
    records = get_demo("gov_opportunities")
    for r in records:
        if r.get("id") == opp_id:
            return r

    raise HTTPException(status_code=404, detail="Government opportunity not found")
