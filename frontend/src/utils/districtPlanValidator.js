export function isValidDistrictPlan(res) {
  if (!res || typeof res !== 'object' || !res.district) {
    return false;
  }
  const hasTotalJobs = typeof res.total_jobs === 'number';
  const hasSkillGaps = Array.isArray(res.skill_gaps);
  const hasCourses = Array.isArray(res.local_courses);
  const hasRoles = Array.isArray(res.top_roles) || Array.isArray(res.top_demanded_roles);
  return hasTotalJobs && (hasSkillGaps || hasCourses || hasRoles);
}
