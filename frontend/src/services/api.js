const rawBase = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const cleanBase = rawBase.replace(/\/+$/, '');
const API_BASE = cleanBase.endsWith('/api') ? cleanBase : `${cleanBase}/api`;

async function fetchJSON(endpoint, options = {}) {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });
    if (!res.ok) {
      throw new Error(`API error: ${res.status} ${res.statusText}`);
    }
    return await res.json();
  } catch (err) {
    console.warn(`[SkillSetu API] Failed to fetch from ${endpoint}:`, err);
    throw err;
  }
}

export const api = {
  // Health
  getHealth: () => fetchJSON('/health'),

  // Skills & Demand
  getSkills: () => fetchJSON('/skills'),
  getSkill: (id) => fetchJSON(`/skills/${id}`),
  getJobs: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return fetchJSON(`/jobs${query ? `?${query}` : ''}`);
  },
  getJobDemand: (groupBy = 'district') => fetchJSON(`/jobs/demand?group_by=${groupBy}`),

  // Skill Gaps
  getGaps: (district) => fetchJSON(district ? `/gaps/district/${district}` : '/gaps'),

  // Courses & Health
  getCourses: () => fetchJSON('/courses'),
  getCourseRecommendations: () => fetchJSON('/courses/recommendations'),

  // Signals & Forecasts
  getSignals: () => fetchJSON('/signals'),
  getForecasts: (skillId) => fetchJSON(skillId ? `/forecast/skill/${skillId}` : '/forecast'),

  // Districts
  getDistricts: () => fetchJSON('/districts'),
  getDistrictPlan: (name) => fetchJSON(`/districts/${name}/plan`),

  // Student & Passport
  getStudents: () => fetchJSON('/students'),
  getStudentPassport: (id) => fetchJSON(`/student/${id}/passport`),
  getStudentRoadmap: (id) => fetchJSON(`/student/${id}/roadmap`),

  // AI Copilot
  askCopilot: (question, role = 'student') => fetchJSON('/copilot/ask', {
    method: 'POST',
    body: JSON.stringify({ question, role }),
  }),

  // Employer Validation
  getEmployerValidations: () => fetchJSON('/employer/validate'),
  submitEmployerFeedback: (feedbackId, status, notes = null, proficiency = null) => fetchJSON('/employer/feedback', {
    method: 'POST',
    body: JSON.stringify({
      feedback_id: feedbackId,
      status,
      notes,
      proficiency_required: proficiency,
    }),
  }),
};
