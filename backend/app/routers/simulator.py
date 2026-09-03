"""Policy What-If Simulator — government decision-support projections.

All results are deterministic derivations from existing SkillSetu data.
Every projection is labelled SIMULATED ESTIMATE per spec Section 20.
"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.db import get_demo
from app.services.gap_engine import compute_gaps

router = APIRouter()


class WhatIfScenario(BaseModel):
    scenario_type: str  # "capacity_increase" | "curriculum_stale" | "new_course"
    skill_category: str | None = None  # e.g. "AI/ML", "Electric Vehicles", "Cloud"
    district: str | None = None
    capacity_change_pct: int = 30  # for capacity_increase
    stale_years: int = 2  # for curriculum_stale


# ---------------------------------------------------------------------------
# Helpers — reuse existing demo data, no new data files
# ---------------------------------------------------------------------------

def _skill_categories() -> list[str]:
    """Return sorted unique categories from the skills table."""
    return sorted({s.get("category", "") for s in get_demo("skills") if s.get("category")})


def _baseline_metrics(district: str | None = None) -> dict:
    """Compute current-state metrics from existing data."""
    gaps = compute_gaps(district=district)
    try:
        from app.repositories.supabase_repository import list_courses
        courses = list_courses()
    except Exception:
        courses = get_demo("courses")
    placements = get_demo("placements")

    # Filter courses/placements by district if requested
    if district:
        dl = district.lower()
        course_ids = {c["id"] for c in courses if c.get("district", "").lower() == dl}
        courses_filtered = [c for c in courses if c["id"] in course_ids]
        placements_filtered = [p for p in placements if p.get("course_id") in course_ids]
    else:
        courses_filtered = courses
        placements_filtered = placements

    total_seats = sum(c.get("enrolment_count", 0) for c in courses_filtered)
    total_students = sum(p.get("student_count", 0) for p in placements_filtered)
    total_placed = sum(p.get("placed_count", 0) for p in placements_filtered)
    placement_rate = round(total_placed / total_students * 100, 1) if total_students else 0
    avg_gap = round(sum(g["gap_pct"] for g in gaps) / len(gaps), 1) if gaps else 0
    top_gap_skills = [{"skill": g["skill_name"], "gap_pct": g["gap_pct"], "category": g.get("category", "")} for g in gaps[:8]]

    return {
        "total_training_seats": total_seats,
        "total_students": total_students,
        "total_placed": total_placed,
        "placement_rate_pct": placement_rate,
        "avg_skill_gap_pct": avg_gap,
        "courses_count": len(courses_filtered),
        "top_gap_skills": top_gap_skills,
    }


def _simulate_capacity_increase(baseline: dict, scenario: WhatIfScenario) -> dict:
    """Simulate increasing training capacity for a skill category/district."""
    pct = max(1, min(200, scenario.capacity_change_pct))
    gaps = compute_gaps(district=scenario.district)
    try:
        from app.repositories.supabase_repository import list_courses
        courses = list_courses()
    except Exception:
        courses = get_demo("courses")
    course_skills_data = get_demo("course_skills")
    skills_map = {s["id"]: s for s in get_demo("skills")}

    # Identify which courses/skills are affected by the category filter
    cat_lower = (scenario.skill_category or "").lower()
    if cat_lower:
        cat_skill_ids = {s["id"] for s in get_demo("skills") if s.get("category", "").lower() == cat_lower}
        affected_course_ids = {cs["course_id"] for cs in course_skills_data if cs["skill_id"] in cat_skill_ids}
    else:
        cat_skill_ids = {s["id"] for s in get_demo("skills")}
        affected_course_ids = {c["id"] for c in courses}

    # Apply district filter
    if scenario.district:
        dl = scenario.district.lower()
        affected_course_ids = {c["id"] for c in courses if c["id"] in affected_course_ids and c.get("district", "").lower() == dl}

    affected_courses = [c for c in courses if c["id"] in affected_course_ids]
    added_seats = sum(round(c.get("enrolment_count", 0) * pct / 100) for c in affected_courses)

    # Estimate gap reduction: more seats → better coverage → smaller gap
    # ponytail: simple linear model — gap reduces proportionally to capacity increase, capped at 60% reduction
    reduction_factor = min(0.6, pct / 100 * 0.5)
    affected_gaps = [g for g in gaps if cat_lower == "" or g.get("category", "").lower() == cat_lower]
    projected_gaps = []
    for g in affected_gaps:
        new_gap = max(0, round(g["gap_pct"] * (1 - reduction_factor), 1))
        projected_gaps.append({
            "skill": g["skill_name"],
            "current_gap_pct": g["gap_pct"],
            "projected_gap_pct": new_gap,
            "reduction_pct": round(g["gap_pct"] - new_gap, 1),
        })
    projected_gaps.sort(key=lambda x: x["reduction_pct"], reverse=True)

    new_total_seats = baseline["total_training_seats"] + added_seats
    # Placement rate improves proportionally (diminishing returns)
    placement_boost = min(15, round(pct * 0.12, 1))
    new_placement_rate = min(99, round(baseline["placement_rate_pct"] + placement_boost, 1))
    new_avg_gap = round(baseline["avg_skill_gap_pct"] * (1 - reduction_factor), 1)

    # Trainer/equipment estimates: 1 trainer per 20 seats, 1 equipment unit per 10 seats
    trainers_needed = max(1, round(added_seats / 20))
    equipment_units = max(1, round(added_seats / 10))

    return {
        "projected_total_seats": new_total_seats,
        "seats_added": added_seats,
        "projected_placement_rate_pct": new_placement_rate,
        "placement_rate_change": round(new_placement_rate - baseline["placement_rate_pct"], 1),
        "projected_avg_gap_pct": new_avg_gap,
        "gap_reduction_pct": round(baseline["avg_skill_gap_pct"] - new_avg_gap, 1),
        "trainers_required": trainers_needed,
        "equipment_units_required": equipment_units,
        "affected_courses_count": len(affected_courses),
        "affected_courses": [{"id": c["id"], "name": c["name"], "district": c.get("district", "")} for c in affected_courses[:10]],
        "affected_skill_gaps": projected_gaps[:10],
    }


def _simulate_curriculum_stale(baseline: dict, scenario: WhatIfScenario) -> dict:
    """Simulate what happens if curriculum is NOT updated for N years."""
    years = max(1, min(5, scenario.stale_years))
    from app.repositories.supabase_repository import list_skill_forecasts
    forecasts = list_skill_forecasts()
    skills_map = {s["id"]: s for s in get_demo("skills")}

    # Skills with rising trends will worsen the gap
    rising_skills = [f for f in forecasts if f.get("trend") == "rising"]
    cat_lower = (scenario.skill_category or "").lower()
    if cat_lower:
        rising_skills = [f for f in rising_skills if skills_map.get(f["skill_id"], {}).get("category", "").lower() == cat_lower]

    # Each year of stale curriculum worsens gap by ~8% compounding
    decay_per_year = 0.08
    total_decay = 1 - (1 - decay_per_year) ** years
    projected_gap = min(85, round(baseline["avg_skill_gap_pct"] * (1 + total_decay * 2), 1))
    placement_decline = min(30, round(years * 4.5, 1))
    projected_placement = max(20, round(baseline["placement_rate_pct"] - placement_decline, 1))

    # Identify skills that would become critical
    emerging_uncovered = []
    for f in rising_skills[:12]:
        skill = skills_map.get(f["skill_id"], {})
        # ponytail: confidence degrades with stale curricula
        projected_confidence = max(30, f.get("confidence", 75) - years * 8)
        emerging_uncovered.append({
            "skill": skill.get("name", "Unknown"),
            "category": skill.get("category", ""),
            "current_demand": f.get("current_demand", ""),
            "future_demand": f.get("future_demand", ""),
            "curriculum_coverage_risk": "NOT COVERED" if projected_confidence < 50 else "DECLINING",
        })

    return {
        "stale_years": years,
        "projected_avg_gap_pct": projected_gap,
        "gap_increase_pct": round(projected_gap - baseline["avg_skill_gap_pct"], 1),
        "projected_placement_rate_pct": projected_placement,
        "placement_decline_pct": round(baseline["placement_rate_pct"] - projected_placement, 1),
        "emerging_skills_uncovered": len(emerging_uncovered),
        "emerging_skills_at_risk": emerging_uncovered,
        "industry_shortage_warning": f"Projected {len(emerging_uncovered)} critical skill areas will lack qualified graduates after {years} year(s) without curriculum revision.",
    }


def _simulate_new_course(baseline: dict, scenario: WhatIfScenario) -> dict:
    """Simulate adding a new course targeting a specific skill category/district."""
    cat_lower = (scenario.skill_category or "").lower()
    gaps = compute_gaps(district=scenario.district)
    skills_map = {s["id"]: s for s in get_demo("skills")}

    # Find the top gaps in the target category
    if cat_lower:
        target_gaps = [g for g in gaps if g.get("category", "").lower() == cat_lower]
    else:
        target_gaps = gaps[:5]

    # A new course typically covers 40-60 seats and addresses 3-5 skills
    new_seats = 50
    skills_addressed = min(5, len(target_gaps))
    addressed_skills = []
    total_gap_reduction = 0
    for g in target_gaps[:skills_addressed]:
        # New course reduces this skill's gap by ~30-50%
        reduction = round(g["gap_pct"] * 0.35, 1)
        total_gap_reduction += reduction
        addressed_skills.append({
            "skill": g["skill_name"],
            "current_gap_pct": g["gap_pct"],
            "projected_gap_pct": round(g["gap_pct"] - reduction, 1),
            "reduction_pct": reduction,
        })

    avg_gap_improvement = round(total_gap_reduction / len(target_gaps), 1) if target_gaps else 0
    new_avg_gap = max(0, round(baseline["avg_skill_gap_pct"] - avg_gap_improvement * 0.3, 1))
    placement_boost = min(8, round(skills_addressed * 1.2, 1))
    new_placement = min(99, round(baseline["placement_rate_pct"] + placement_boost, 1))

    return {
        "new_course_seats": new_seats,
        "skills_addressed_count": skills_addressed,
        "skills_addressed": addressed_skills,
        "projected_avg_gap_pct": new_avg_gap,
        "gap_improvement_pct": round(baseline["avg_skill_gap_pct"] - new_avg_gap, 1),
        "projected_placement_rate_pct": new_placement,
        "placement_boost_pct": round(new_placement - baseline["placement_rate_pct"], 1),
        "trainers_required": max(1, round(new_seats / 20)),
        "equipment_units_required": max(1, round(new_seats / 10)),
        "suggested_district": scenario.district or "Pune",
        "suggested_category": scenario.skill_category or "AI/ML",
    }


# ---------------------------------------------------------------------------
# API endpoint
# ---------------------------------------------------------------------------

@router.post("/simulator/whatif")
async def run_whatif(scenario: WhatIfScenario):
    """Run a policy what-if simulation and return baseline vs. projected metrics.

    All projections are labelled SIMULATED ESTIMATE per spec Section 20.
    """
    baseline = _baseline_metrics(district=scenario.district)

    simulators = {
        "capacity_increase": _simulate_capacity_increase,
        "curriculum_stale": _simulate_curriculum_stale,
        "new_course": _simulate_new_course,
    }
    simulate_fn = simulators.get(scenario.scenario_type)
    if not simulate_fn:
        # Fallback: treat unknown type as capacity_increase
        simulate_fn = _simulate_capacity_increase

    projection = simulate_fn(baseline, scenario)

    return {
        "label": "SIMULATED ESTIMATE",
        "disclaimer": "These projections are decision-support estimates derived from current SkillSetu data. They are not guaranteed real-world predictions.",
        "scenario": {
            "type": scenario.scenario_type,
            "skill_category": scenario.skill_category,
            "district": scenario.district,
            "parameters": {
                "capacity_change_pct": scenario.capacity_change_pct,
                "stale_years": scenario.stale_years,
            },
        },
        "baseline": baseline,
        "projection": projection,
        "available_categories": _skill_categories(),
        "confidence_level": "medium",
    }


@router.get("/simulator/categories")
async def get_categories():
    """Return available skill categories for the simulator dropdowns."""
    return {"categories": _skill_categories()}
