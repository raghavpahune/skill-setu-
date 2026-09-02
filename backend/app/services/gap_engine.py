"""Skill Gap Engine — computes demand vs. coverage gaps."""
from collections import Counter
from app.db import get_demo
from app.services.career_recommendation_engine import is_live_employer_demand


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

    # Phase 14: Incorporate validated first-party employer demands
    employer_demands = get_demo("employer_demands")
    skills_by_name = {s["name"].lower(): s["id"] for s in skills_map.values()}
    validated_demands = [
        d for d in employer_demands
        if is_live_employer_demand(d) and (d.get("validation_status") or d.get("status") or "").upper() in ("VALIDATED", "APPROVED")
    ]
    if district:
        validated_demands = [d for d in validated_demands if d.get("district", "").lower() == district.lower()]

    for ed in validated_demands:
        weight = max(1, ed.get("openings_count", ed.get("positions_count", 10)) // 10)
        req_skills = ed.get("required_skills") or ed.get("skills") or []
        for sk in req_skills:
            sk_name = sk if isinstance(sk, str) else sk.get("name", "")
            sid = sk if sk in skills_map else skills_by_name.get(str(sk_name).lower())
            if sid:
                demand_counts[sid] += weight
                total_jobs += weight

    # Coverage: weighted by course enrolment
    # A skill taught in a course with 120 students at level 4/5 is better covered
    # than a skill in a course with 30 students at level 2/5
    courses_to_use = [c for c in courses if c.get("district", "").lower() == district.lower()] if district else courses
    course_enrolment = {c["id"]: (c.get("enrolment_count") or c.get("enrolment_capacity", 60)) for c in courses_to_use}
    total_enrolment = sum(course_enrolment.values()) or 1

    # For each skill: sum(coverage_level/5 * course_enrolment) / total_enrolment
    skill_coverage_weighted = {}
    existing_cs_course_ids = set()
    for cs in course_skills_data:
        cid = cs.get("course_id")
        if cid in course_enrolment:
            existing_cs_course_ids.add(cid)
            sid = cs["skill_id"]
            lvl = cs.get("coverage_level", 0)
            enrol = course_enrolment.get(cid, 0)
            weighted = (lvl / 5) * enrol
            skill_coverage_weighted[sid] = skill_coverage_weighted.get(sid, 0) + weighted

    # Phase 25: Incorporate first-party user-submitted courses not present in static course_skills
    for c in courses_to_use:
        cid = c.get("id")
        c_skills = c.get("skills") or c.get("skills_taught") or []
        if cid not in existing_cs_course_ids and c_skills:
            enrol = c.get("enrolment_count") or c.get("enrolment_capacity", 60)
            lvl = min(5, max(1, c.get("nsqf_level", 5) - 1))
            for sk in c_skills:
                sk_name = sk if isinstance(sk, str) else sk.get("name", "")
                sid = sk if sk in skills_map else skills_by_name.get(str(sk_name).lower())
                if sid:
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
