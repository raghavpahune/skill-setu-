"""Skill Gap Engine — computes demand vs. coverage gaps."""
from collections import Counter
from app.db import get_demo


def compute_gaps(district: str | None = None) -> list[dict]:
    """Compute skill gaps: demand_score - coverage_score per skill.

    Demand score: % of job postings requiring this skill (0-100).
    Coverage score: weighted average of course coverage × training capacity.
    Gap = demand - coverage. Negative gaps are clamped to 0.
    """
    jobs = get_demo("jobs")
    job_skills = get_demo("job_skills")
    course_skills_data = get_demo("course_skills")
    courses = get_demo("courses")
    skills_map = {s["id"]: s for s in get_demo("skills")}

    # Filter jobs by district if specified
    if district:
        district_job_ids = {j["id"] for j in jobs if j["district"].lower() == district.lower()}
        filtered_js = [js for js in job_skills if js["job_id"] in district_job_ids]
        total_jobs = len(district_job_ids) or 1
    else:
        filtered_js = job_skills
        total_jobs = len(jobs) or 1

    # Demand: what % of all job postings require this skill
    demand_counts = Counter(js["skill_id"] for js in filtered_js)

    # Coverage: weighted by course enrolment
    # A skill taught in a course with 120 students at level 4/5 is better covered
    # than a skill in a course with 30 students at level 2/5
    course_enrolment = {c["id"]: c.get("enrolment_count", 0) for c in courses}
    total_enrolment = sum(course_enrolment.values()) or 1

    # For each skill: sum(coverage_level/5 * course_enrolment) / total_enrolment
    skill_coverage_weighted = {}
    for cs in course_skills_data:
        sid = cs["skill_id"]
        lvl = cs.get("coverage_level", 0)
        enrol = course_enrolment.get(cs["course_id"], 0)
        weighted = (lvl / 5) * enrol
        skill_coverage_weighted[sid] = skill_coverage_weighted.get(sid, 0) + weighted

    gaps = []
    for sid, count in demand_counts.items():
        skill = skills_map.get(sid, {})
        # Demand: % of jobs needing this skill (cap at 100)
        demand_pct = min(100, round(count / total_jobs * 100))
        # Coverage: weighted training capacity as % of total
        coverage_raw = skill_coverage_weighted.get(sid, 0) / total_enrolment * 100
        coverage_pct = min(100, round(coverage_raw))
        gap_pct = max(0, demand_pct - coverage_pct)

        if gap_pct >= 15:
            priority = "CRITICAL"
        elif gap_pct >= 8:
            priority = "HIGH"
        elif gap_pct >= 3:
            priority = "MEDIUM"
        else:
            priority = "LOW"

        gaps.append({
            "skill_id": sid,
            "skill_name": skill.get("name", "Unknown"),
            "category": skill.get("category", ""),
            "demand_pct": demand_pct,
            "coverage_pct": coverage_pct,
            "gap_pct": gap_pct,
            "priority": priority,
            "demand_count": count,
        })

    gaps.sort(key=lambda x: x["gap_pct"], reverse=True)
    return gaps
