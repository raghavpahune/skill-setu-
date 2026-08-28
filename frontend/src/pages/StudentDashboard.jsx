import React, { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/Layout';
import StatCard from '../components/StatCard';
import PassportRadar from '../components/PassportRadar';
import StudentAlertsFeed from '../components/StudentAlertsFeed';
import SkillExplainabilityModal from '../components/SkillExplainabilityModal';
import { api } from '../services/api';

const DEFAULT_STUDENTS = [
  { user_id: 'stu-001', name: 'Aarav Patil', target_role: 'AI Engineer', skill_match_pct: 52 },
  { user_id: 'stu-002', name: 'Priya Deshmukh', target_role: 'Data Analyst', skill_match_pct: 38 },
  { user_id: 'stu-003', name: 'Rohan Kulkarni', target_role: 'EV Technician', skill_match_pct: 30 },
  { user_id: 'stu-004', name: 'Sneha Joshi', target_role: 'Cybersecurity Analyst', skill_match_pct: 45 },
  { user_id: 'stu-005', name: 'Vikram Shinde', target_role: 'Cloud Architect', skill_match_pct: 35 },
];

function EmptyState({
  title = 'No records available',
  message = 'No data points were returned for this section.',
  icon,
  action,
}) {
  return (
    <div className="py-8 px-4 text-center rounded-xl border border-dashed border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30">
      <div className="w-8 h-8 mx-auto mb-2 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-400 dark:text-slate-500">
        {icon || (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
          </svg>
        )}
      </div>
      <h4 className="text-xs font-bold text-slate-700 dark:text-slate-300">{title}</h4>
      <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 max-w-sm mx-auto">{message}</p>
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}

function ErrorBanner({ message, onRetry }) {
  return (
    <div className="mb-6 p-4 rounded-xl border border-rose-200 dark:border-rose-900/60 bg-rose-50/60 dark:bg-rose-950/30 text-rose-800 dark:text-rose-300 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-xs">
      <div className="flex items-center gap-2.5">
        <svg className="w-5 h-5 text-rose-600 dark:text-rose-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <div>
          <h4 className="text-xs font-bold">Data Communication Issue</h4>
          <p className="text-[11px] text-rose-700 dark:text-rose-400 mt-0.5">{message}</p>
        </div>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors shrink-0 cursor-pointer"
        >
          Retry Connection
        </button>
      )}
    </div>
  );
}

function SkeletonKpiCard() {
  return (
    <div className="p-4 sm:p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 animate-pulse">
      <div className="h-3 w-24 bg-slate-200 dark:bg-slate-800 rounded mb-2.5"></div>
      <div className="h-8 w-28 bg-slate-200 dark:bg-slate-800 rounded mb-2"></div>
      <div className="h-3 w-32 bg-slate-100 dark:bg-slate-800/60 rounded"></div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="p-6 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 animate-pulse space-y-4">
      <div className="h-4 w-48 bg-slate-200 dark:bg-slate-800 rounded"></div>
      <div className="h-3 w-64 bg-slate-100 dark:bg-slate-800/60 rounded"></div>
      <div className="h-48 bg-slate-100 dark:bg-slate-800/40 rounded-lg"></div>
    </div>
  );
}

function SkeletonRoadmapStep() {
  return (
    <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 animate-pulse flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center">
      <div className="flex items-start gap-3 w-full sm:w-3/4">
        <div className="w-8 h-8 rounded-lg bg-slate-200 dark:bg-slate-700 shrink-0"></div>
        <div className="space-y-2 w-full">
          <div className="h-4 w-40 bg-slate-200 dark:bg-slate-700 rounded"></div>
          <div className="h-3 w-full bg-slate-100 dark:bg-slate-800 rounded"></div>
        </div>
      </div>
      <div className="h-8 w-24 bg-slate-200 dark:bg-slate-700 rounded self-end sm:self-center"></div>
    </div>
  );
}

export default function StudentDashboard() {
  const [students, setStudents] = useState(DEFAULT_STUDENTS);
  const [selectedStudentId, setSelectedStudentId] = useState('stu-001');
  const [passport, setPassport] = useState(null);
  const [roadmap, setRoadmap] = useState(null);
  const [schemes, setSchemes] = useState([]);
  const [opportunities, setOpportunities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [passportError, setPassportError] = useState(null);
  const [roadmapError, setRoadmapError] = useState(null);
  const [filterTab, setFilterTab] = useState('all'); // 'all' | 'acquired' | 'gaps'

  // Skill Explainability Modal state (PROJECT_SPEC Section 18)
  const [explainModalOpen, setExplainModalOpen] = useState(false);
  const [selectedExplainSkill, setSelectedExplainSkill] = useState('');
  const [selectedExplainSkillName, setSelectedExplainSkillName] = useState('');

  const handleOpenExplainability = (skillIdOrName, skillName = '') => {
    setSelectedExplainSkill(skillIdOrName);
    setSelectedExplainSkillName(skillName || skillIdOrName);
    setExplainModalOpen(true);
  };

  // Load students, schemes, and opportunities on mount
  useEffect(() => {
    api.getStudents()
      .then((res) => {
        if (Array.isArray(res) && res.length > 0) {
          setStudents(res);
          if (!res.some((s) => s.user_id === selectedStudentId)) {
            setSelectedStudentId(res[0].user_id);
          }
        }
      })
      .catch((err) => {
        console.warn('Failed to load candidate list:', err);
      });

    api.getSchemes({ limit: 4 })
      .then((res) => {
        if (Array.isArray(res)) {
          setSchemes(res);
        }
      })
      .catch(() => {});

    api.getOpportunities({ limit: 4 })
      .then((res) => {
        if (Array.isArray(res)) {
          setOpportunities(res);
        }
      })
      .catch(() => {});
  }, []);

  // Fetch passport and roadmap whenever candidate changes
  const fetchStudentData = () => {
    if (!selectedStudentId) return;
    setLoading(true);
    setPassportError(null);
    setRoadmapError(null);

    Promise.allSettled([
      api.getStudentPassport(selectedStudentId),
      api.getStudentRoadmap(selectedStudentId),
    ]).then(([pRes, rRes]) => {
      if (pRes.status === 'fulfilled' && pRes.value && !pRes.value.error) {
        setPassport(pRes.value);
      } else {
        const errMsg = pRes.status === 'rejected'
          ? (pRes.reason?.message || 'Failed to connect to passport API')
          : (pRes.value?.error || 'Candidate passport record not found');
        setPassportError(errMsg);
      }

      if (rRes.status === 'fulfilled' && rRes.value && !rRes.value.error) {
        setRoadmap(rRes.value);
      } else {
        const errMsg = rRes.status === 'rejected'
          ? (rRes.reason?.message || 'Failed to connect to roadmap API')
          : (rRes.value?.error || 'Curriculum roadmap not available for this role');
        setRoadmapError(errMsg);
      }
      setLoading(false);
    });
  };

  useEffect(() => {
    fetchStudentData();
  }, [selectedStudentId]);

  // Derived calculations for Comparison Flow
  const comparisonData = useMemo(() => {
    if (!passport) return { items: [], acquired: [], gaps: [], additional: [] };

    const currentMap = new Map((passport.current_skills || []).map((c) => [c.skill_id, c]));
    const requiredSkills = passport.required_skills || [];

    const items = requiredSkills.map((req) => {
      const cur = currentMap.get(req.skill_id);
      const isAcquired = !!cur;
      const proficiency = cur?.proficiency || 'none';
      const profScore = { beginner: 35, intermediate: 70, advanced: 100 }[proficiency] || 0;
      const isProficient = proficiency === 'advanced' || proficiency === 'intermediate';

      // Check if skill is in recommended roadmap
      const roadmapStep = (roadmap?.roadmap || []).find((s) => s.skill_id === req.skill_id);

      return {
        skill_id: req.skill_id,
        skill_name: req.skill_name || req.skill_id,
        category: req.category || cur?.category || 'Technical',
        nsqf_level: req.nsqf_level || cur?.nsqf_level || null,
        proficiency,
        profScore,
        isAcquired,
        isProficient,
        status: !isAcquired ? 'gap' : isProficient ? 'proficient' : 'upskill',
        roadmapStep: roadmapStep?.step || null,
      };
    });

    const acquired = items.filter((i) => i.isAcquired);
    const gaps = items.filter((i) => !i.isAcquired);

    // Cross-functional / secondary skills held by student outside role requirements
    const requiredIds = new Set(requiredSkills.map((r) => r.skill_id));
    const additional = (passport.current_skills || []).filter((c) => !requiredIds.has(c.skill_id));

    return { items, acquired, gaps, additional };
  }, [passport, roadmap]);

  const filteredComparisonItems = useMemo(() => {
    if (filterTab === 'acquired') return comparisonData.acquired;
    if (filterTab === 'gaps') return comparisonData.gaps;
    return comparisonData.items;
  }, [comparisonData, filterTab]);

  return (
    <Layout>
      {/* Header & Candidate Profile Switcher */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              Student Dynamic Skill Passport
            </h1>
            <span className="text-[11px] font-mono px-2 py-0.5 bg-teal-50 dark:bg-teal-950 text-teal-800 dark:text-teal-300 font-semibold rounded border border-teal-200 dark:border-teal-800">
              NSQF Aligned
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Personalized competency verification, labour-market benchmark alignment, and validated learning roadmap
          </p>
        </div>

        {/* Candidate Profile Selector */}
        <div className="flex items-center gap-2 bg-white dark:bg-slate-900 p-1.5 px-3 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs self-start md:self-auto">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">Candidate Profile:</span>
          <select
            value={selectedStudentId}
            onChange={(e) => setSelectedStudentId(e.target.value)}
            disabled={loading}
            className="px-2.5 py-1 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-xs font-bold text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-teal-500 cursor-pointer disabled:opacity-50"
          >
            {students.map((s) => (
              <option key={s.user_id} value={s.user_id}>
                {s.name} ({s.target_role})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Global Error Banner */}
      {passportError && (
        <ErrorBanner
          message={`Failed to retrieve skill passport data for candidate (${passportError}).`}
          onRetry={fetchStudentData}
        />
      )}

      {/* Dynamic Alignment Workflow Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 dark:from-slate-900 dark:via-teal-950/40 dark:to-slate-900 border border-slate-800 rounded-xl p-4 sm:p-5 mb-6 text-white flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-sm">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2 text-[11px] text-teal-400 font-semibold uppercase tracking-wider font-mono">
            <span>Career Pathway Sequence</span>
          </div>
          <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 text-xs font-medium">
            <span className="bg-slate-800/90 border border-slate-700 px-2.5 py-1 rounded text-slate-200">
              1. Current Competencies
            </span>
            <span className="text-teal-400 font-bold">→</span>
            <span className="bg-rose-950/80 border border-rose-800 px-2.5 py-1 rounded text-rose-300">
              2. Priority Skill Gaps
            </span>
            <span className="text-teal-400 font-bold">→</span>
            <span className="bg-teal-950/80 border border-teal-800 px-2.5 py-1 rounded text-teal-300">
              3. Recommended Pathway
            </span>
            <span className="text-teal-400 font-bold">→</span>
            <span className="bg-emerald-950/80 border border-emerald-800 px-2.5 py-1 rounded text-emerald-300">
              4. Industry Placement
            </span>
          </div>
        </div>

        <Link
          to="/student/copilot"
          className="px-3.5 py-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold rounded-lg shadow-xs transition-colors shrink-0 flex items-center gap-1.5 cursor-pointer"
        >
          <span>Consult Career Copilot</span>
          <span>→</span>
        </Link>
      </div>

      {/* Top KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-8">
        {loading ? (
          <>
            <SkeletonKpiCard />
            <SkeletonKpiCard />
            <SkeletonKpiCard />
            <SkeletonKpiCard />
          </>
        ) : (
          <>
            <StatCard
              title="Candidate Profile"
              value={passport?.name || 'Aarav Patil'}
              subtitle={`ID: ${selectedStudentId}`}
              icon="🎓"
            />
            <StatCard
              title="Target Career Role"
              value={passport?.target_role || 'AI Engineer'}
              subtitle="Industry benchmark target"
              icon="🎯"
              color="teal"
            />
            <StatCard
              title="Competency Match"
              value={`${passport?.skill_match_pct || 0}%`}
              subtitle="Match vs target requirements"
              icon="📊"
              color={
                (passport?.skill_match_pct || 0) >= 70
                  ? 'teal'
                  : (passport?.skill_match_pct || 0) >= 40
                  ? 'amber'
                  : 'rose'
              }
            />
            <StatCard
              title="Critical Skill Gaps"
              value={`${passport?.missing_skills?.length || 0} Skills`}
              subtitle="Prerequisites to bridge"
              icon="⚡"
              color="rose"
            />
          </>
        )}
      </div>

      {/* Grid: Skill Passport Radar & Competency Comparison */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-8">
        {/* Left: Competency Benchmark Radar (5 cols on lg) */}
        <div className="lg:col-span-5 bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100 dark:border-slate-800">
              <div>
                <h3 className="font-bold text-slate-900 dark:text-white text-base">
                  Competency Benchmark Radar
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Candidate mastery vs 100% employer benchmark
                </p>
              </div>
              <span className="text-[11px] font-mono px-2 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold rounded border border-slate-200 dark:border-slate-700">
                NCO-2015
              </span>
            </div>

            {loading ? (
              <div className="h-72 flex items-center justify-center animate-pulse">
                <div className="w-48 h-48 rounded-full border-4 border-dashed border-slate-200 dark:border-slate-800"></div>
              </div>
            ) : (
              <PassportRadar
                currentSkills={passport?.current_skills || []}
                requiredSkills={passport?.required_skills || []}
              />
            )}
          </div>

          <div className="flex flex-wrap justify-center items-center gap-4 sm:gap-6 mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 text-xs font-medium">
            <span className="flex items-center gap-1.5 text-teal-700 dark:text-teal-400">
              <span className="w-3 h-3 rounded-full bg-teal-600 dark:bg-teal-400"></span> Candidate Proficiency
            </span>
            <span className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400">
              <span className="w-3 h-3 rounded-full bg-slate-300 dark:bg-slate-700 border border-dashed border-slate-400"></span> Employer Target (100%)
            </span>
          </div>
        </div>

        {/* Right: Competency Comparison Flow Matrix (7 cols on lg) */}
        <div className="lg:col-span-7 bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs flex flex-col justify-between">
          <div>
            {/* Matrix Header & Tabs */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-100 dark:border-slate-800">
              <div>
                <h3 className="font-bold text-slate-900 dark:text-white text-base">
                  Skills Comparison Matrix
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Direct evaluation of student skills against <strong>{passport?.target_role || 'Target Role'}</strong> requirements
                </p>
              </div>

              {/* Segmented Filter Buttons */}
              <div className="inline-flex rounded-lg border border-slate-200 dark:border-slate-700 p-0.5 bg-slate-50 dark:bg-slate-800/80 text-[11px] font-semibold self-start sm:self-auto">
                <button
                  onClick={() => setFilterTab('all')}
                  className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer ${
                    filterTab === 'all'
                      ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-2xs font-bold'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  All Target ({comparisonData.items.length})
                </button>
                <button
                  onClick={() => setFilterTab('acquired')}
                  className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer ${
                    filterTab === 'acquired'
                      ? 'bg-white dark:bg-slate-900 text-emerald-700 dark:text-emerald-300 shadow-2xs font-bold'
                      : 'text-slate-600 dark:text-slate-400 hover:text-emerald-600'
                  }`}
                >
                  Acquired ({comparisonData.acquired.length})
                </button>
                <button
                  onClick={() => setFilterTab('gaps')}
                  className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer ${
                    filterTab === 'gaps'
                      ? 'bg-white dark:bg-slate-900 text-rose-700 dark:text-rose-300 shadow-2xs font-bold'
                      : 'text-slate-600 dark:text-slate-400 hover:text-rose-600'
                  }`}
                >
                  Gaps ({comparisonData.gaps.length})
                </button>
              </div>
            </div>

            {/* Matrix Content */}
            {loading ? (
              <div className="space-y-3 py-2 animate-pulse">
                <div className="h-8 bg-slate-100 dark:bg-slate-800 rounded"></div>
                <div className="h-12 bg-slate-50 dark:bg-slate-800/50 rounded"></div>
                <div className="h-12 bg-slate-50 dark:bg-slate-800/50 rounded"></div>
                <div className="h-12 bg-slate-50 dark:bg-slate-800/50 rounded"></div>
              </div>
            ) : filteredComparisonItems.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 dark:text-slate-400 font-semibold border-b border-slate-200 dark:border-slate-700">
                    <tr>
                      <th className="p-2.5">Role Competency</th>
                      <th className="p-2.5">Current Proficiency</th>
                      <th className="p-2.5">Target Benchmark</th>
                      <th className="p-2.5 text-right">Alignment Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {filteredComparisonItems.map((item) => (
                      <tr key={item.skill_id} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors">
                        <td className="p-2.5">
                          <div className="font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                            <span>{item.skill_name}</span>
                          </div>
                          <div className="flex items-center gap-1.5 mt-0.5">
                            {item.category && (
                              <span className="text-[10px] text-slate-500 dark:text-slate-400 font-medium">
                                {item.category}
                              </span>
                            )}
                            {item.nsqf_level && (
                              <span className="text-[9px] font-mono px-1 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                                NSQF L{item.nsqf_level}
                              </span>
                            )}
                          </div>
                        </td>

                        {/* Current Proficiency Bar */}
                        <td className="p-2.5">
                          <div className="w-28 sm:w-36">
                            <div className="flex justify-between text-[10px] font-mono mb-1">
                              <span className="font-semibold capitalize text-slate-700 dark:text-slate-300">
                                {item.proficiency !== 'none' ? item.proficiency : 'Not Acquired'}
                              </span>
                              <span className="text-slate-500">{item.score}%</span>
                            </div>
                            <div className="h-1.5 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full transition-all ${
                                  item.score >= 70
                                    ? 'bg-emerald-500 dark:bg-emerald-400'
                                    : item.score >= 35
                                    ? 'bg-amber-500 dark:bg-amber-400'
                                    : 'bg-slate-300 dark:bg-slate-700'
                                }`}
                                style={{ width: `${item.score}%` }}
                              ></div>
                            </div>
                          </div>
                        </td>

                        {/* Target Requirement */}
                        <td className="p-2.5">
                          <span className="inline-flex items-center gap-1 text-[11px] font-mono font-medium text-slate-700 dark:text-slate-300">
                            <span className="w-1.5 h-1.5 rounded-full bg-teal-500"></span>
                            100% Benchmark
                          </span>
                        </td>

                        {/* Status / Action Badge & Explain Trigger */}
                        <td className="p-2.5 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            {item.status === 'proficient' ? (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                                <span>✓</span> Proficient
                              </span>
                            ) : item.status === 'upskill' ? (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
                                <span>↑</span> Upskill Target
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-50 dark:bg-rose-950 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800">
                                <span>⚠️</span> Critical Gap
                              </span>
                            )}
                            {item.status !== 'proficient' && (
                              <button
                                onClick={() => handleOpenExplainability(item.skill_id, item.skill_name)}
                                className="px-1.5 py-0.5 text-[10px] font-bold rounded text-teal-700 dark:text-teal-300 bg-teal-50 dark:bg-teal-950 hover:bg-teal-100 dark:hover:bg-teal-900 border border-teal-200 dark:border-teal-800 transition-colors cursor-pointer"
                                title="View 5-dimension grounded evidence why this skill is needed"
                              >
                                Why? ⓘ
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState
                title={filterTab === 'gaps' ? 'Zero Skill Gaps Detected' : 'No Competencies Found'}
                message={
                  filterTab === 'gaps'
                    ? 'Candidate currently satisfies all required competencies for this target role benchmark.'
                    : 'No skills matched the current filter selection.'
                }
              />
            )}

            {/* Cross-functional / Additional Acquired Skills Panel */}
            {comparisonData.additional.length > 0 && (
              <div className="mt-5 pt-4 border-t border-slate-100 dark:border-slate-800">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider flex items-center gap-1">
                    <span>✨</span> Cross-Functional Secondary Competencies
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">
                    {comparisonData.additional.length} Bonus Skills
                  </span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {comparisonData.additional.map((sk) => (
                    <span
                      key={sk.skill_id}
                      className="inline-flex items-center gap-1 px-2 py-1 bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 text-xs font-semibold rounded-lg border border-slate-200 dark:border-slate-700"
                    >
                      <span>{sk.skill_name}</span>
                      <span className="text-[10px] uppercase font-mono px-1 py-0.2 bg-white dark:bg-slate-900 rounded border border-slate-200 dark:border-slate-700 text-slate-500">
                        {sk.proficiency}
                      </span>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="mt-6 pt-3 border-t border-slate-100 dark:border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
            <span className="text-xs text-slate-500 dark:text-slate-400">
              Need personalized curriculum guidance for these gaps?
            </span>
            <Link
              to="/student/copilot"
              className="px-3 py-1.5 bg-slate-900 dark:bg-teal-600 text-white text-xs font-bold rounded-lg hover:bg-slate-800 dark:hover:bg-teal-700 transition-colors shadow-2xs cursor-pointer"
            >
              Ask Career Copilot →
            </Link>
          </div>
        </div>
      </div>

      {/* Guided Career & Skill Roadmap */}
      <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs mb-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5 pb-3 border-b border-slate-100 dark:border-slate-800">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-slate-900 dark:text-white text-lg">
                Evidence-Based Career & Learning Roadmap
              </h3>
              <span className="text-xs font-bold px-2.5 py-0.5 bg-teal-50 dark:bg-teal-950 text-teal-800 dark:text-teal-300 rounded-full border border-teal-200 dark:border-teal-800">
                Labour-Market Validated
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Prioritized sequential pathway to bridge competency deficits and achieve full eligibility for{' '}
              <strong>{passport?.target_role || 'Target Role'}</strong>
            </p>
          </div>

          <div className="text-xs font-mono text-slate-500 dark:text-slate-400 self-start sm:self-auto">
            Target Horizon: 2025–2027
          </div>
        </div>

        {/* Multi-Stage Progression Overview Bar */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-2 mb-6 text-xs">
          <div className="p-2.5 rounded-lg bg-emerald-50/70 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-900/60">
            <span className="text-[10px] font-bold text-emerald-800 dark:text-emerald-300 uppercase font-mono block">
              Stage 1 • Baseline
            </span>
            <p className="font-semibold text-slate-900 dark:text-white text-[11px] mt-0.5">
              {comparisonData.acquired.length} Verified Skills
            </p>
          </div>

          <div className="p-2.5 rounded-lg bg-rose-50/70 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/60">
            <span className="text-[10px] font-bold text-rose-800 dark:text-rose-300 uppercase font-mono block">
              Stage 2 • Priority Gaps
            </span>
            <p className="font-semibold text-slate-900 dark:text-white text-[11px] mt-0.5">
              {comparisonData.gaps.length} Target Deficits
            </p>
          </div>

          <div className="p-2.5 rounded-lg bg-teal-50/70 dark:bg-teal-950/30 border border-teal-200 dark:border-teal-900/60">
            <span className="text-[10px] font-bold text-teal-800 dark:text-teal-300 uppercase font-mono block">
              Stage 3 • Learning Track
            </span>
            <p className="font-semibold text-slate-900 dark:text-white text-[11px] mt-0.5">
              {roadmap?.roadmap?.length || 0} Sequenced Modules
            </p>
          </div>

          <div className="p-2.5 rounded-lg bg-slate-100 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700">
            <span className="text-[10px] font-bold text-slate-700 dark:text-slate-300 uppercase font-mono block">
              Stage 4 • Milestone
            </span>
            <p className="font-semibold text-slate-900 dark:text-white text-[11px] mt-0.5">
              {passport?.target_role || 'Target Role'} Ready
            </p>
          </div>
        </div>

        {/* Roadmap Steps */}
        {roadmapError ? (
          <ErrorBanner
            message={`Failed to retrieve recommended roadmap (${roadmapError}).`}
            onRetry={fetchStudentData}
          />
        ) : loading ? (
          <div className="space-y-3">
            <SkeletonRoadmapStep />
            <SkeletonRoadmapStep />
            <SkeletonRoadmapStep />
          </div>
        ) : roadmap?.roadmap && roadmap.roadmap.length > 0 ? (
          <div className="space-y-3.5">
            {roadmap.roadmap.map((step, idx) => (
              <div
                key={step.skill_id || idx}
                className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 hover:border-teal-300 dark:hover:border-teal-600 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-2xs"
              >
                <div className="flex items-start gap-3.5 w-full sm:w-3/4">
                  <div className="w-8 h-8 rounded-lg bg-slate-900 dark:bg-teal-600 text-white font-bold text-sm flex items-center justify-center shrink-0 shadow-2xs">
                    {step.step || idx + 1}
                  </div>
                  <div className="space-y-1.5 w-full">
                    <div className="flex flex-wrap items-center gap-2">
                      <h4 className="font-bold text-slate-900 dark:text-white text-sm">
                        {step.skill_name}
                      </h4>
                      {step.category && (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 font-medium">
                          {step.category}
                        </span>
                      )}
                      {step.nsqf_level && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-mono">
                          NSQF L{step.nsqf_level}
                        </span>
                      )}
                      <span className="px-2 py-0.5 rounded text-[10px] bg-teal-100 dark:bg-teal-950 text-teal-800 dark:text-teal-300 font-semibold uppercase border border-teal-200 dark:border-teal-800 font-mono">
                        Trend: {step.trend || 'rising'}
                      </span>
                      {step.confidence && (
                        <span className="text-[10px] text-slate-500 dark:text-slate-400 font-mono">
                          • {step.confidence}% Demand Confidence
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                      <button
                        onClick={() => handleOpenExplainability(step.skill_id, step.skill_name)}
                        className="text-teal-800 dark:text-teal-300 font-bold hover:underline cursor-pointer inline-flex items-center gap-1 mr-1"
                        title="Click to open 5-dimension grounded explainability breakdown"
                      >
                        <span>Why learn this?</span>
                        <span className="text-[9px] font-mono px-1 py-0.2 bg-teal-100 dark:bg-teal-900 rounded">5D Evidence ⓘ</span>
                      </button>{' '}
                      {step.why}
                    </p>
                  </div>
                </div>

                <div className="shrink-0 self-end sm:self-center flex items-center gap-2">
                  <button
                    onClick={() => handleOpenExplainability(step.skill_id, step.skill_name)}
                    className="text-xs font-bold text-teal-700 dark:text-teal-300 hover:text-teal-900 dark:hover:text-teal-100 bg-teal-50 dark:bg-teal-950/60 px-3 py-2 rounded-lg border border-teal-200 dark:border-teal-800 shadow-2xs hover:bg-teal-100 dark:hover:bg-teal-900 transition-colors inline-block cursor-pointer"
                  >
                    Explain Demand ⓘ
                  </button>
                  <Link
                    to="/student/copilot"
                    className="text-xs font-bold text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 bg-white dark:bg-slate-800 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 shadow-2xs hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors inline-block cursor-pointer"
                  >
                    Curriculum Advice →
                  </Link>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No Curriculum Roadmap Steps Available"
            message={`All core prerequisites for ${passport?.target_role || 'this role'} appear to be satisfied, or the curriculum pathway is being updated.`}
            action={
              <Link
                to="/student/copilot"
                className="inline-block px-4 py-1.5 bg-teal-600 text-white rounded-lg text-xs font-bold hover:bg-teal-700 transition-colors"
              >
                Ask Career Copilot
              </Link>
            }
          />
        )}
      </div>

      {/* Section 19: Personalized Industry & Technology Alerts Feed */}
      <div className="mb-8">
        <StudentAlertsFeed
          studentId={selectedStudentId}
          onOpenExplainability={handleOpenExplainability}
        />
      </div>

      {/* Eligible Government Schemes & NAPS Opportunities */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* State Welfare Schemes */}
        <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100 dark:border-slate-800">
              <div>
                <h3 className="font-bold text-slate-900 dark:text-white text-base">
                  Eligible State Welfare & Scholarship Schemes
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Government funding, fee waivers & tool grants for vocational candidates
                </p>
              </div>
              <span className="text-[10px] font-mono font-semibold px-2 py-0.5 bg-teal-50 dark:bg-teal-950 text-teal-800 dark:text-teal-300 rounded border border-teal-200 dark:border-teal-800">
                MahaDBT / OGD
              </span>
            </div>

            {schemes.length > 0 ? (
              <div className="space-y-3">
                {schemes.map((s) => (
                  <div
                    key={s.id}
                    className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700/80 hover:border-teal-300 dark:hover:border-teal-600 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <h4 className="font-bold text-slate-900 dark:text-white text-xs leading-snug">
                        {s.title}
                      </h4>
                      {s.max_amount && (
                        <span className="text-[11px] font-mono font-bold text-teal-700 dark:text-teal-400 shrink-0">
                          ₹{s.max_amount.toLocaleString('en-IN')}
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-600 dark:text-slate-300 line-clamp-2 mb-2">
                      {s.benefit_description}
                    </p>
                    <div className="flex items-center justify-between text-[10px] text-slate-500 dark:text-slate-400 pt-1 border-t border-slate-200/60 dark:border-slate-700/60">
                      <span className="font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-300">
                        {s.scheme_type?.replace('_', ' ')}
                      </span>
                      {s.application_portal_url && (
                        <a
                          href={s.application_portal_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-teal-600 dark:text-teal-400 font-bold hover:underline"
                        >
                          Apply on Portal →
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 py-4 text-center">Loading welfare schemes...</p>
            )}
          </div>
        </div>

        {/* NAPS & Vocational Opportunities */}
        <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100 dark:border-slate-800">
              <div>
                <h3 className="font-bold text-slate-900 dark:text-white text-base">
                  Approved Apprenticeships & Trainee Vacancies
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Direct placements aligned with NAPS & PMKVY in Maharashtra
                </p>
              </div>
              <span className="text-[10px] font-mono font-semibold px-2 py-0.5 bg-blue-50 dark:bg-blue-950 text-blue-800 dark:text-blue-300 rounded border border-blue-200 dark:border-blue-800">
                NAPS / PMKVY
              </span>
            </div>

            {opportunities.length > 0 ? (
              <div className="space-y-3">
                {opportunities.map((opp) => (
                  <div
                    key={opp.id}
                    className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700/80 hover:border-blue-300 dark:hover:border-blue-600 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <div>
                        <h4 className="font-bold text-slate-900 dark:text-white text-xs leading-snug">
                          {opp.title}
                        </h4>
                        <p className="text-[11px] text-slate-500 dark:text-slate-400">
                          {opp.company} • <span className="font-semibold text-slate-700 dark:text-slate-300">{opp.district}</span>
                        </p>
                      </div>
                      {opp.stipend_amount && (
                        <span className="text-[11px] font-mono font-bold text-blue-700 dark:text-blue-400 shrink-0">
                          ₹{opp.stipend_amount.toLocaleString('en-IN')}/mo
                        </span>
                      )}
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-slate-500 dark:text-slate-400 pt-2 mt-1 border-t border-slate-200/60 dark:border-slate-700/60">
                      <span className="px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200 uppercase font-mono font-semibold">
                        {opp.opportunity_type?.replace('_', ' ')}
                      </span>
                      {opp.apply_url && (
                        <a
                          href={opp.apply_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 dark:text-blue-400 font-bold hover:underline"
                        >
                          View & Apply →
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 py-4 text-center">Loading opportunities...</p>
            )}
          </div>
        </div>
      </div>

      {/* Section 18: "Why Should I Learn This?" 5-Dimension Explainability Modal */}
      <SkillExplainabilityModal
        isOpen={explainModalOpen}
        onClose={() => setExplainModalOpen(false)}
        skillQuery={selectedExplainSkill}
        studentId={selectedStudentId}
        skillNameFallback={selectedExplainSkillName}
      />
    </Layout>
  );
}
