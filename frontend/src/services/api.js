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

  // AI Copilot
  askCopilot: (question, role = 'student') => fetchJSON('/copilot/ask', {
    method: 'POST',
    body: JSON.stringify({ question, role }),
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
