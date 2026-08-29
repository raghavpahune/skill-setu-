function getApiBase() {
  // 1. Explicit Vite environment variable (baked in at build time)
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl && typeof envUrl === 'string' && envUrl.trim()) {
    const clean = envUrl.trim().replace(/\/+$/, '');
    return clean.endsWith('/api') ? clean : `${clean}/api`;
  }

  // 2. Runtime override via window or localStorage (allows instant configuration without rebuild)
  if (typeof window !== 'undefined') {
    const localOverride = window.localStorage?.getItem('skillsetu_api_url') || window.__SKILLSETU_API_URL__;
    if (localOverride && typeof localOverride === 'string' && localOverride.trim()) {
      const clean = localOverride.trim().replace(/\/+$/, '');
      return clean.endsWith('/api') ? clean : `${clean}/api`;
    }

    // 3. Localhost development
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      return 'http://127.0.0.1:8000/api';
    }
  }

  // 4. Production default relative URL (works seamlessly with same-origin or Vercel rewrites)
  return '/api';
}

const API_BASE = getApiBase();

async function fetchJSON(endpoint, options = {}) {
  const base = getApiBase();
  const url = `${base}${endpoint}`;
  try {
    const res = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!res.ok) {
      const errText = await res.text().catch(() => '');
      let errMsg = `API error: ${res.status} ${res.statusText}`;
      try {
        const errJson = JSON.parse(errText);
        if (errJson.detail) errMsg = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
        if (errJson.message) errMsg = errJson.message;
      } catch {
        if (errText && errText.length < 120 && !errText.includes('<html')) {
          errMsg = errText;
        }
      }
      throw new Error(errMsg);
    }

    const contentType = res.headers.get('content-type') || '';
    if (!contentType.includes('application/json')) {
      const text = await res.text();
      if (text.includes('<!DOCTYPE') || text.includes('<html')) {
        throw new Error(`Endpoint ${endpoint} returned HTML instead of JSON. Backend service may be connecting.`);
      }
      try {
        return JSON.parse(text);
      } catch {
        return text;
      }
    }

    return await res.json();
  } catch (err) {
    console.warn(`[SkillSetu API] Failed to fetch from ${url}:`, err.message || err);
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
  getStudentAlertDomains: () => fetchJSON('/student/alert-domains'),
  getStudentIndustryAlerts: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return fetchJSON(`/student/industry-alerts${query ? `?${query}` : ''}`);
  },
  getSkillExplainability: (skill, studentId = null) => {
    const query = studentId ? `?student_id=${encodeURIComponent(studentId)}` : '';
    return fetchJSON(`/student/skill-explainability/${encodeURIComponent(skill)}${query}`);
  },

  // Student Data Collection & Assessment (Phase 12)
  getAssessmentQuizQuestions: () => fetchJSON('/student/assessment/quiz-questions'),
  submitStudentAssessment: (payload) => fetchJSON('/student/assessment', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  getStudentAssessments: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return fetchJSON(`/student/assessments${query ? `?${query}` : ''}`);
  },
  getStudentAssessment: (id) => fetchJSON(`/student/assessment/${encodeURIComponent(id)}`),

  // Admin Data Management (Phase 13)
  getAdminAssessments: (params = {}, adminKey = '') => {
    const key = adminKey || (typeof window !== 'undefined' ? window.localStorage?.getItem('skillsetu_admin_key') : '') || 'demo-admin-key-2026';
    const query = new URLSearchParams(params).toString();
    return fetchJSON(`/admin/assessments${query ? `?${query}` : ''}`, {
      headers: { 'X-Admin-Key': key },
    });
  },
  getAdminAssessment: (id, adminKey = '') => {
    const key = adminKey || (typeof window !== 'undefined' ? window.localStorage?.getItem('skillsetu_admin_key') : '') || 'demo-admin-key-2026';
    return fetchJSON(`/admin/assessments/${encodeURIComponent(id)}`, {
      headers: { 'X-Admin-Key': key },
    });
  },
  getAdminAssessmentStats: (adminKey = '') => {
    const key = adminKey || (typeof window !== 'undefined' ? window.localStorage?.getItem('skillsetu_admin_key') : '') || 'demo-admin-key-2026';
    return fetchJSON('/admin/assessments/stats/summary', {
      headers: { 'X-Admin-Key': key },
    });
  },
  deleteAdminAssessment: (id, adminKey = '') => {
    const key = adminKey || (typeof window !== 'undefined' ? window.localStorage?.getItem('skillsetu_admin_key') : '') || 'demo-admin-key-2026';
    return fetchJSON(`/admin/assessments/${encodeURIComponent(id)}`, {
      method: 'DELETE',
      headers: { 'X-Admin-Key': key },
    });
  },

  // AI Copilot
  askCopilot: (question, role = 'student', district = null, studentId = null) => fetchJSON('/copilot/ask', {
    method: 'POST',
    body: JSON.stringify({ question, role, district, student_id: studentId }),
  }),
  explainCareerCopilot: (studentId, question = null, district = null) => fetchJSON('/copilot/explain-career', {
    method: 'POST',
    body: JSON.stringify({ student_id: studentId, question, district }),
  }),


  // Schemes & Student Welfare
  getSchemes: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return fetchJSON(`/schemes${query ? `?${query}` : ''}`);
  },
  getSchemeCategories: () => fetchJSON('/schemes/categories'),
  getScheme: (id) => fetchJSON(`/schemes/${id}`),

  // Opportunities (Apprenticeships, Internships, Vocational Training, Jobs)
  getOpportunities: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return fetchJSON(`/opportunities${query ? `?${query}` : ''}`);
  },
  getOpportunitiesSummary: () => fetchJSON('/opportunities/summary'),
  getOpportunity: (id) => fetchJSON(`/opportunities/${id}`),

  // Data Ingestion & Automated Sync
  getSyncStatus: () => fetchJSON('/sync/status'),
  getSyncLogs: (limit = 20, offset = 0) => fetchJSON(`/sync/logs?limit=${limit}&offset=${offset}`),
  triggerSync: (source = 'data.gov.in', adminKey = '') => fetchJSON(`/sync/trigger?source=${source}`, {
    method: 'POST',
    headers: adminKey ? { 'X-Admin-Key': adminKey } : {},
  }),

  // AI Diagnostic
  getHealthAI: () => fetchJSON('/health/ai'),

  // Employer Validation & Demand Hub (Phase 8 & 14)
  getEmployerValidations: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return fetchJSON(`/employer/validate${query ? `?${query}` : ''}`);
  },
  submitEmployerFeedback: (feedbackId, status, notes = null, proficiency = null) => fetchJSON('/employer/feedback', {
    method: 'POST',
    body: JSON.stringify({
      feedback_id: feedbackId,
      status,
      notes,
      proficiency_required: proficiency,
    }),
  }),
  getEmployerDemands: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return fetchJSON(`/employer/demands${query ? `?${query}` : ''}`);
  },
  getEmployerDemand: (id) => fetchJSON(`/employer/demands/${encodeURIComponent(id)}`),
  submitEmployerDemand: (demandData) => fetchJSON('/employer/demands', {
    method: 'POST',
    body: JSON.stringify(demandData),
  }),
  getDifficultSkills: () => fetchJSON('/employer/difficult-skills'),
  getEmployerSummary: () => fetchJSON('/employer/summary'),

  // Admin Employer Demand Management & Validation (Phase 14)
  getAdminEmployerDemands: (params = {}, adminKey = '') => {
    const key = adminKey || (typeof window !== 'undefined' ? window.localStorage?.getItem('skillsetu_admin_key') : '') || 'demo-admin-key-2026';
    const query = new URLSearchParams(params).toString();
    return fetchJSON(`/admin/employer/demands${query ? `?${query}` : ''}`, {
      headers: { 'X-Admin-Key': key },
    });
  },
  updateAdminEmployerDemandStatus: (id, status, notes = '', adminKey = '') => {
    const key = adminKey || (typeof window !== 'undefined' ? window.localStorage?.getItem('skillsetu_admin_key') : '') || 'demo-admin-key-2026';
    return fetchJSON(`/admin/employer/demands/${encodeURIComponent(id)}/status`, {
      method: 'PATCH',
      headers: { 'X-Admin-Key': key },
      body: JSON.stringify({ status, admin_notes: notes }),
    });
  },
  deleteAdminEmployerDemand: (id, adminKey = '') => {
    const key = adminKey || (typeof window !== 'undefined' ? window.localStorage?.getItem('skillsetu_admin_key') : '') || 'demo-admin-key-2026';
    return fetchJSON(`/admin/employer/demands/${encodeURIComponent(id)}`, {
      method: 'DELETE',
      headers: { 'X-Admin-Key': key },
    });
  },

  // Policy What-If Simulator
  runSimulation: (scenario) => fetchJSON('/simulator/whatif', {
    method: 'POST',
    body: JSON.stringify(scenario),
  }),
  getSimulatorCategories: () => fetchJSON('/simulator/categories'),

  // Government Opportunities (Phase 15)
  getGovOpportunities: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return fetchJSON(`/gov/opportunities${query ? `?${query}` : ''}`);
  },
  getGovOpportunityTypes: () => fetchJSON('/gov/opportunities/types'),
  getGovOpportunity: (id) => fetchJSON(`/gov/opportunities/${encodeURIComponent(id)}`),
  getRecommendedSchemes: (studentId) => fetchJSON(`/schemes/recommended/${encodeURIComponent(studentId)}`),
  getRecommendedGovOpportunities: (studentId) => fetchJSON(`/gov/opportunities/recommended/${encodeURIComponent(studentId)}`),

  // Admin Government Opportunities (Phase 15)
  getAdminGovOpportunities: (params = {}, adminKey = '') => {
    const key = adminKey || (typeof window !== 'undefined' ? window.localStorage?.getItem('skillsetu_admin_key') : '') || 'demo-admin-key-2026';
    const query = new URLSearchParams(params).toString();
    return fetchJSON(`/admin/gov/opportunities${query ? `?${query}` : ''}`, {
      headers: { 'X-Admin-Key': key },
    });
  },
  createAdminGovOpportunity: (data, adminKey = '') => {
    const key = adminKey || (typeof window !== 'undefined' ? window.localStorage?.getItem('skillsetu_admin_key') : '') || 'demo-admin-key-2026';
    return fetchJSON('/admin/gov/opportunities', {
      method: 'POST',
      headers: { 'X-Admin-Key': key },
      body: JSON.stringify(data),
    });
  },
  updateAdminGovOpportunity: (id, data, adminKey = '') => {
    const key = adminKey || (typeof window !== 'undefined' ? window.localStorage?.getItem('skillsetu_admin_key') : '') || 'demo-admin-key-2026';
    return fetchJSON(`/admin/gov/opportunities/${encodeURIComponent(id)}`, {
      method: 'PATCH',
      headers: { 'X-Admin-Key': key },
      body: JSON.stringify(data),
    });
  },
  deleteAdminGovOpportunity: (id, adminKey = '') => {
    const key = adminKey || (typeof window !== 'undefined' ? window.localStorage?.getItem('skillsetu_admin_key') : '') || 'demo-admin-key-2026';
    return fetchJSON(`/admin/gov/opportunities/${encodeURIComponent(id)}`, {
      method: 'DELETE',
      headers: { 'X-Admin-Key': key },
    });
  },

  // Career Recommendations & Skill-Gap Engine (Phase 16)
  getStudentCareerRecommendations: (studentId) => {
    return fetchJSON(`/student/recommendations/${encodeURIComponent(studentId)}`);
  },
  explainStudentRecommendationsAi: (studentId, prompt = null) => {
    return fetchJSON(`/student/recommendations/${encodeURIComponent(studentId)}/explain-ai`, {
      method: 'POST',
      body: JSON.stringify({ prompt }),
    });
  },
};


