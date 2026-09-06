import test from 'node:test';
import assert from 'node:assert/strict';
import {
  ALLOWED_PROFICIENCIES,
  normalizeProficiency,
  deduplicateSkills,
  formatStudentProfilePayload,
  formatEmployeeProfilePayload,
  validateStudentProfile,
  validateEmployeeProfile,
} from './src/utils/profileValidator.js';

test('normalizeProficiency bounds strictly to allowed levels', () => {
  for (const p of ALLOWED_PROFICIENCIES) {
    assert.equal(normalizeProficiency(p), p);
    assert.equal(normalizeProficiency(`  ${p.toUpperCase()}  `), p);
  }
  assert.equal(normalizeProficiency('master'), 'beginner');
  assert.equal(normalizeProficiency(''), 'beginner');
  assert.equal(normalizeProficiency(null), 'beginner');
  assert.equal(normalizeProficiency(undefined), 'beginner');
  assert.equal(normalizeProficiency(42), 'beginner');
});

test('deduplicateSkills deduplicates skills case-insensitively and bounds proficiency', () => {
  const input = [
    { skill_name: 'Python', proficiency: 'beginner' },
    { skill_name: 'python', proficiency: 'advanced' },
    { skill_name: '  PYTHON  ', proficiency: 'expert', skill_id: 'sk-python-01' },
    { skill_name: 'React', proficiency: 'intermediate' },
    { skill_name: '', proficiency: 'advanced' },
    null,
  ];

  const result = deduplicateSkills(input);
  assert.equal(result.length, 2);

  const pythonSkill = result.find((s) => s.skill_name.toLowerCase() === 'python');
  assert.ok(pythonSkill);
  assert.equal(pythonSkill.proficiency, 'expert');
  assert.equal(pythonSkill.skill_id, 'sk-python-01');

  const reactSkill = result.find((s) => s.skill_name.toLowerCase() === 'react');
  assert.ok(reactSkill);
  assert.equal(reactSkill.proficiency, 'intermediate');
});

test('deduplicateSkills handles non-array input safely', () => {
  assert.deepEqual(deduplicateSkills(null), []);
  assert.deepEqual(deduplicateSkills(undefined), []);
  assert.deepEqual(deduplicateSkills('string'), []);
});

test('formatStudentProfilePayload sanitizes and deduplicates fields correctly', () => {
  const form = {
    institution: '  COEP Tech University  ',
    degree: ' B.Tech Computer Engineering ',
    education_level: ' Undergraduate (B.Tech / B.E / B.Sc) ',
    academic_year: ' Final Year ',
    graduation_year: '2026',
    desired_role: ' AI Engineer ',
    preferred_location: ' Pune, Maharashtra ',
    career_interests: [' Machine Learning ', 'Robotics', ' Machine Learning '],
    skills: [
      { skill_name: 'PyTorch', proficiency: 'advanced' },
      { skill_name: 'pytorch', proficiency: 'expert' },
    ],
    projects: [
      { name: ' AI Drone ', description: ' Edge AI ', skills: [' PyTorch ', 'ROS '], url: ' https://github.com/test ' },
      { name: '', description: 'Empty name project' },
    ],
    certifications: [
      { name: ' TensorFlow Dev ', issuer: ' Google ', issue_date: '2025-01-01', url: ' https://cert.example.com ' },
      { name: ' Incomplete cert ', issuer: '' },
    ],
    courses: [
      { course_name: ' Deep Learning Specialization ', provider: ' Coursera ', status: ' Completed ' },
    ],
  };

  const payload = formatStudentProfilePayload(form);

  assert.equal(payload.institution, 'COEP Tech University');
  assert.equal(payload.degree, 'B.Tech Computer Engineering');
  assert.equal(payload.education_level, 'Undergraduate (B.Tech / B.E / B.Sc)');
  assert.equal(payload.academic_year, 'Final Year');
  assert.equal(payload.graduation_year, 2026);
  assert.equal(payload.desired_role, 'AI Engineer');
  assert.equal(payload.target_role, 'AI Engineer');
  assert.equal(payload.preferred_location, 'Pune, Maharashtra');

  assert.deepEqual(payload.career_interests, ['Machine Learning', 'Robotics']);

  assert.equal(payload.skills.length, 1);
  assert.equal(payload.skills[0].skill_name, 'pytorch');
  assert.equal(payload.skills[0].proficiency, 'expert');

  assert.equal(payload.projects.length, 1);
  assert.equal(payload.projects[0].name, 'AI Drone');
  assert.deepEqual(payload.projects[0].skills, ['PyTorch', 'ROS']);

  assert.equal(payload.certifications.length, 1);
  assert.equal(payload.certifications[0].name, 'TensorFlow Dev');

  assert.equal(payload.courses.length, 1);
  assert.equal(payload.courses[0].course_name, 'Deep Learning Specialization');
});

test('formatEmployeeProfilePayload normalizes experience and deduplicates skills', () => {
  const form = {
    current_role: ' Senior Cloud Architect ',
    years_of_experience: ' 7.5 ',
    industry: ' IT Services ',
    education: ' M.Tech Software ',
    target_role: ' VP Engineering ',
    preferred_location: ' Mumbai ',
    skills: [
      { skill_name: 'Kubernetes', proficiency: 'expert' },
      { skill_name: 'kubernetes', proficiency: 'expert' },
      { skill_name: 'AWS', proficiency: 'advanced' },
    ],
    certifications: [
      { name: ' AWS Solutions Architect ', issuer: ' Amazon ', issue_date: '2024-05', url: '' },
    ],
  };

  const payload = formatEmployeeProfilePayload(form);

  assert.equal(payload.current_role, 'Senior Cloud Architect');
  assert.equal(payload.years_of_experience, 7.5);
  assert.equal(payload.industry, 'IT Services');
  assert.equal(payload.target_role, 'VP Engineering');
  assert.equal(payload.skills.length, 2);
  assert.equal(payload.certifications.length, 1);
  assert.equal(payload.certifications[0].url, null);
});

test('validateStudentProfile rejects out-of-range graduation years', () => {
  assert.equal(validateStudentProfile({ graduation_year: 2026 }).isValid, true);
  assert.equal(validateStudentProfile({ graduation_year: 1950 }).isValid, false);
  assert.equal(validateStudentProfile({ graduation_year: 2150 }).isValid, false);
  assert.equal(validateStudentProfile(null).isValid, false);
});

test('validateEmployeeProfile enforces required role and valid experience bounds', () => {
  assert.equal(validateEmployeeProfile({ current_role: 'DevOps Lead', years_of_experience: 5 }).isValid, true);
  assert.equal(validateEmployeeProfile({ current_role: 'DevOps Lead', years_of_experience: 70 }).isValid, true);
  assert.equal(validateEmployeeProfile({ current_role: 'DevOps Lead', years_of_experience: 71 }).isValid, false);
  assert.equal(validateEmployeeProfile({ current_role: '', years_of_experience: 5 }).isValid, false);
  assert.equal(validateEmployeeProfile({ current_role: 'DevOps Lead', years_of_experience: -2 }).isValid, false);
  assert.equal(validateEmployeeProfile(null).isValid, false);
});
