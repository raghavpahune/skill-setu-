import test from 'node:test';
import assert from 'node:assert/strict';
import { isValidDistrictPlan } from './src/utils/districtPlanValidator.js';

const EMPTY_DISTRICT_PLAN = (district) => ({
  district,
  total_jobs: 0,
  total_courses: 0,
  total_enrolment: 0,
  top_roles: [],
  top_demanded_roles: [],
  industry_demand: [],
  local_courses: [],
  skill_gaps: [],
  top_skills: [],
  top_demanded_skills: [],
  required_equipment: [],
  trainer_programs: [],
  courses_needing_review: [],
  recommended_courses: [],
  nearby_institutes: [],
  required_training_seats: 0,
  required_trainers_count: 0,
  total_equipment_budget_inr: 0,
  expected_impact: {
    projected_placement_lift_pct: 0,
    projected_skill_deficit_reduction_pct: 0,
    target_placed_students: 0,
    total_budget_estimate_inr: 0,
  },
});

test('valid backend district plan response is accepted by production validator', () => {
  const validBackendResponse = {
    district: 'Pune',
    total_jobs: 42,
    total_courses: 15,
    total_enrolment: 1200,
    top_roles: [{ role: 'CNC Operator', count: 12 }],
    top_demanded_roles: [{ role: 'CNC Operator', count: 12 }],
    top_skills: [{ skill_id: 'sk-1', name: 'CNC Milling', count: 18 }],
    top_demanded_skills: [{ skill_id: 'sk-1', name: 'CNC Milling', count: 18 }],
    skill_gaps: [{ skill_id: 'sk-1', skill_name: 'CNC Milling', gap_pct: 45 }],
    local_courses: [{ id: 'c-1', name: 'CNC Machining', institute: 'ITI Pune', enrolment: 50, placement_rate: 80 }],
    industry_demand: [{ industry: 'Manufacturing', count: 25 }],
    recommended_courses: [{ trade_name: 'Advanced CNC', target_enrolment_seats: 40 }],
    courses_needing_review: [],
    required_training_seats: 80,
    required_equipment: [{ item: 'CNC Simulator', units: 2, unit_cost_inr: 250000 }],
    total_equipment_budget_inr: 500000,
    required_trainers_count: 4,
    trainer_programs: [{ program: 'Master CNC Trainer', duration: '4 weeks', certifying_body: 'MSBTE' }],
    nearby_institutes: [{ name: 'ITI Pune', district: 'Pune', type: 'Direct ITI', active_courses_count: 5 }],
    expected_impact: {
      projected_placement_lift_pct: 18.5,
      projected_skill_deficit_reduction_pct: 40.0,
      target_placed_students: 68,
      total_budget_estimate_inr: 1100000,
    },
  };

  assert.equal(isValidDistrictPlan(validBackendResponse), true);
});

test('valid backend response with zero jobs and empty lists is accepted as authoritative zero data', () => {
  const validEmptyResponse = {
    district: 'Solapur',
    total_jobs: 0,
    total_courses: 0,
    total_enrolment: 0,
    top_roles: [],
    top_demanded_roles: [],
    top_skills: [],
    top_demanded_skills: [],
    skill_gaps: [],
    local_courses: [],
    industry_demand: [],
    recommended_courses: [],
    courses_needing_review: [],
    required_training_seats: 0,
    required_equipment: [],
    total_equipment_budget_inr: 0,
    required_trainers_count: 0,
    trainer_programs: [],
    nearby_institutes: [],
    expected_impact: {
      projected_placement_lift_pct: 0,
      projected_skill_deficit_reduction_pct: 0,
      target_placed_students: 0,
      total_budget_estimate_inr: 0,
    },
  };

  assert.equal(isValidDistrictPlan(validEmptyResponse), true);
});

test('partial payload with district and total_jobs 0 triggers fallback rather than setPlan', () => {
  const partialPayload = {
    district: 'Pune',
    total_jobs: 0,
  };

  assert.equal(isValidDistrictPlan(partialPayload), false);

  let planState = null;
  let errorState = false;

  if (isValidDistrictPlan(partialPayload)) {
    planState = partialPayload;
  } else {
    errorState = true;
    planState = EMPTY_DISTRICT_PLAN('Pune');
  }

  assert.equal(errorState, true);
  assert.equal(planState.district, 'Pune');
  assert.deepEqual(planState.top_roles, []);
  assert.deepEqual(planState.skill_gaps, []);
  assert.equal(planState.total_jobs, 0);
  assert.equal(planState.expected_impact.projected_placement_lift_pct, 0);
});

test('incomplete response missing required plan fields is rejected by production validator', () => {
  const incompleteResponse = {
    district: 'Kolhapur',
  };

  assert.equal(isValidDistrictPlan(incompleteResponse), false);
});

test('payload missing numeric totals is rejected by production validator', () => {
  const baseResponse = {
    district: 'Pune',
    total_jobs: 10,
    total_courses: 5,
    total_enrolment: 100,
    top_roles: [],
    top_demanded_roles: [],
    top_skills: [],
    top_demanded_skills: [],
    skill_gaps: [],
    local_courses: [],
    industry_demand: [],
    recommended_courses: [],
    courses_needing_review: [],
    required_training_seats: 10,
    required_equipment: [],
    total_equipment_budget_inr: 50000,
    required_trainers_count: 2,
    trainer_programs: [],
    nearby_institutes: [],
    expected_impact: {
      projected_placement_lift_pct: 10,
      projected_skill_deficit_reduction_pct: 20,
      target_placed_students: 8,
      total_budget_estimate_inr: 50000,
    },
  };

  const missingJobs = { ...baseResponse };
  delete missingJobs.total_jobs;
  assert.equal(isValidDistrictPlan(missingJobs), false);

  const stringJobs = { ...baseResponse, total_jobs: 'not-a-number' };
  assert.equal(isValidDistrictPlan(stringJobs), false);

  const nanJobs = { ...baseResponse, total_jobs: Number.NaN };
  assert.equal(isValidDistrictPlan(nanJobs), false);
});

test('payload missing plan array or with non-array is rejected by production validator', () => {
  const baseResponse = {
    district: 'Pune',
    total_jobs: 10,
    total_courses: 5,
    total_enrolment: 100,
    top_roles: [],
    top_demanded_roles: [],
    top_skills: [],
    top_demanded_skills: [],
    skill_gaps: [],
    local_courses: [],
    industry_demand: [],
    recommended_courses: [],
    courses_needing_review: [],
    required_training_seats: 10,
    required_equipment: [],
    total_equipment_budget_inr: 50000,
    required_trainers_count: 2,
    trainer_programs: [],
    nearby_institutes: [],
    expected_impact: {
      projected_placement_lift_pct: 10,
      projected_skill_deficit_reduction_pct: 20,
      target_placed_students: 8,
      total_budget_estimate_inr: 50000,
    },
  };

  const missingGaps = { ...baseResponse };
  delete missingGaps.skill_gaps;
  assert.equal(isValidDistrictPlan(missingGaps), false);

  const nonArrayCourses = { ...baseResponse, local_courses: 'not-an-array' };
  assert.equal(isValidDistrictPlan(nonArrayCourses), false);
});

test('payload missing expected_impact or its numeric metrics is rejected by production validator', () => {
  const baseResponse = {
    district: 'Pune',
    total_jobs: 10,
    total_courses: 5,
    total_enrolment: 100,
    top_roles: [],
    top_demanded_roles: [],
    top_skills: [],
    top_demanded_skills: [],
    skill_gaps: [],
    local_courses: [],
    industry_demand: [],
    recommended_courses: [],
    courses_needing_review: [],
    required_training_seats: 10,
    required_equipment: [],
    total_equipment_budget_inr: 50000,
    required_trainers_count: 2,
    trainer_programs: [],
    nearby_institutes: [],
    expected_impact: {
      projected_placement_lift_pct: 10,
      projected_skill_deficit_reduction_pct: 20,
      target_placed_students: 8,
      total_budget_estimate_inr: 50000,
    },
  };

  const missingImpact = { ...baseResponse };
  delete missingImpact.expected_impact;
  assert.equal(isValidDistrictPlan(missingImpact), false);

  const missingImpactMetric = {
    ...baseResponse,
    expected_impact: {
      projected_placement_lift_pct: 10,
      projected_skill_deficit_reduction_pct: 20,
      target_placed_students: 8,
    },
  };
  assert.equal(isValidDistrictPlan(missingImpactMetric), false);

  const nanImpactMetric = {
    ...baseResponse,
    expected_impact: {
      projected_placement_lift_pct: Number.NaN,
      projected_skill_deficit_reduction_pct: 20,
      target_placed_students: 8,
      total_budget_estimate_inr: 50000,
    },
  };
  assert.equal(isValidDistrictPlan(nanImpactMetric), false);
});

test('null or undefined backend response is rejected by production validator', () => {
  assert.equal(isValidDistrictPlan(null), false);
  assert.equal(isValidDistrictPlan(undefined), false);
  assert.equal(isValidDistrictPlan({}), false);
});
