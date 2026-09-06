import test from 'node:test';
import assert from 'node:assert/strict';

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

function validateAndApplyDistrictPlan(res, districtName, setPlan, setHasError) {
  if (res && res.district && (res.total_jobs !== undefined || res.skill_gaps || res.top_skills || res.local_courses)) {
    setPlan(res);
  } else {
    setHasError(true);
    setPlan(EMPTY_DISTRICT_PLAN(districtName));
  }
}

test('valid backend district plan response is accepted without status kpis or top_shortages', () => {
  let appliedPlan = null;
  let hasError = false;

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

  validateAndApplyDistrictPlan(
    validBackendResponse,
    'Pune',
    (p) => { appliedPlan = p; },
    (e) => { hasError = e; },
  );

  assert.equal(hasError, false);
  assert.equal(appliedPlan.district, 'Pune');
  assert.equal(appliedPlan.total_jobs, 42);
  assert.equal(appliedPlan.top_roles.length, 1);
  assert.equal(appliedPlan.local_courses.length, 1);
});

test('valid backend response with zero jobs and empty lists is accepted as authoritative zero data', () => {
  let appliedPlan = null;
  let hasError = false;

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

  validateAndApplyDistrictPlan(
    validEmptyResponse,
    'Solapur',
    (p) => { appliedPlan = p; },
    (e) => { hasError = e; },
  );

  assert.equal(hasError, false);
  assert.equal(appliedPlan.district, 'Solapur');
  assert.equal(appliedPlan.total_jobs, 0);
  assert.equal(appliedPlan.top_roles.length, 0);
});

test('incomplete response missing required plan fields enters controlled error state and safe empty plan', () => {
  let appliedPlan = null;
  let hasError = false;

  const incompleteResponse = {
    district: 'Kolhapur',
  };

  validateAndApplyDistrictPlan(
    incompleteResponse,
    'Kolhapur',
    (p) => { appliedPlan = p; },
    (e) => { hasError = e; },
  );

  assert.equal(hasError, true);
  assert.equal(appliedPlan.district, 'Kolhapur');
  assert.equal(appliedPlan.total_jobs, 0);
  assert.equal(appliedPlan.total_courses, 0);
  assert.deepEqual(appliedPlan.top_roles, []);
  assert.deepEqual(appliedPlan.skill_gaps, []);
  assert.deepEqual(appliedPlan.required_equipment, []);
  assert.equal(appliedPlan.expected_impact.projected_placement_lift_pct, 0);
  assert.equal(appliedPlan.expected_impact.total_budget_estimate_inr, 0);
});

test('null or undefined backend response enters controlled error state and safe empty plan', () => {
  let appliedPlan = null;
  let hasError = false;

  validateAndApplyDistrictPlan(
    null,
    'Nagpur',
    (p) => { appliedPlan = p; },
    (e) => { hasError = e; },
  );

  assert.equal(hasError, true);
  assert.equal(appliedPlan.district, 'Nagpur');
  assert.equal(appliedPlan.total_jobs, 0);
  assert.equal(appliedPlan.expected_impact.target_placed_students, 0);
});
