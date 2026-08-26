"""District Service — aggregated district-level training plans."""
from collections import Counter
from app.db import get_demo
from app.services.gap_engine import compute_gaps


def get_all_districts() -> list[dict]:
    """List all districts with job counts."""
    jobs = get_demo("jobs")
    counts = Counter(j["district"] for j in jobs)
    return [
        {"name": name, "job_count": count}
        for name, count in sorted(counts.items(), key=lambda x: x[1], reverse=True)
    ]


def get_district_plan(district: str) -> dict:
    """Generate a comprehensive training plan for a district."""
    jobs = get_demo("jobs")
    courses = get_demo("courses")
    skills_map = {s["id"]: s for s in get_demo("skills")}
    job_skills = get_demo("job_skills")
    placements = get_demo("placements")

    # Filter to district
    district_jobs = [j for j in jobs if j["district"].lower() == district.lower()]
    district_courses = [c for c in courses if c["district"].lower() == district.lower()]
    district_job_ids = {j["id"] for j in district_jobs}

    # Top roles
    role_counts = Counter(j["title"] for j in district_jobs)
    top_roles = [{"role": r, "count": c} for r, c in role_counts.most_common(5)]

    # Top skills
    district_js = [js for js in job_skills if js["job_id"] in district_job_ids]
    skill_counts = Counter(js["skill_id"] for js in district_js)
    top_skills = [
        {"skill_id": sid, "skill_name": skills_map.get(sid, {}).get("name", ""), "demand_count": cnt}
        for sid, cnt in skill_counts.most_common(10)
    ]

    # Gaps for this district
    gaps = compute_gaps(district=district)[:10]

    # Local courses
    placement_map = {p["course_id"]: p for p in placements}
    local_courses = []
    for c in district_courses:
        p = placement_map.get(c["id"], {})
        sc = p.get("student_count", 0)
        pc = p.get("placed_count", 0)
        local_courses.append({
            "name": c["name"],
            "institute": c["institute"],
            "enrolment": c.get("enrolment_count", 0),
            "placement_rate": round(pc / sc * 100) if sc else 0,
        })

    # Industry breakdown
    industry_counts = Counter(j["industry"] for j in district_jobs)
    industries = [{"industry": k, "count": v} for k, v in industry_counts.most_common()]

    total_enrolment = sum(c.get("enrolment_count", 0) for c in district_courses)

    return {
        "district": district,
        "total_jobs": len(district_jobs),
        "total_courses": len(district_courses),
        "total_enrolment": total_enrolment,
        "top_roles": top_roles,
        "top_skills": top_skills,
        "skill_gaps": gaps,
        "local_courses": local_courses,
        "industry_demand": industries,
    }
