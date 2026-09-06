export function isValidDistrictPlan(res) {
  if (!res || typeof res !== 'object' || typeof res.district !== 'string' || !res.district.trim()) {
    return false;
  }
  const numericFields = [
    'total_jobs',
    'total_courses',
    'total_enrolment',
    'required_training_seats',
    'required_trainers_count',
    'total_equipment_budget_inr',
  ];
  for (const field of numericFields) {
    if (typeof res[field] !== 'number' || Number.isNaN(res[field])) {
      return false;
    }
  }
  const arrayFields = [
    'top_roles',
    'top_demanded_roles',
    'top_skills',
    'top_demanded_skills',
    'skill_gaps',
    'local_courses',
    'industry_demand',
    'recommended_courses',
    'courses_needing_review',
    'required_equipment',
    'trainer_programs',
    'nearby_institutes',
  ];
  for (const field of arrayFields) {
    if (!Array.isArray(res[field])) {
      return false;
    }
  }
  if (!res.expected_impact || typeof res.expected_impact !== 'object') {
    return false;
  }
  const impactNumericFields = [
    'projected_placement_lift_pct',
    'projected_skill_deficit_reduction_pct',
    'target_placed_students',
    'total_budget_estimate_inr',
  ];
  for (const field of impactNumericFields) {
    if (typeof res.expected_impact[field] !== 'number' || Number.isNaN(res.expected_impact[field])) {
      return false;
    }
  }
  return true;
}
