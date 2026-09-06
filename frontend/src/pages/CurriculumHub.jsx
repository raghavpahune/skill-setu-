import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import Layout from '../components/Layout';
import StatCard from '../components/StatCard';
import { api } from '../services/api';

const RISK_META = {
  CRITICAL_OBSOLETE: {
    label: 'Critical Obsolete',
    badge: 'bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-300 border-rose-300 dark:border-rose-800',
    bar: 'bg-rose-500',
    dot: 'bg-rose-500',
  },
  HIGH_RISK: {
    label: 'High Risk',
    badge: 'bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-800',
    bar: 'bg-amber-400',
    dot: 'bg-amber-400',
  },
  MODERATE: {
    label: 'Moderate',
    badge: 'bg-blue-100 dark:bg-blue-950 text-blue-800 dark:text-blue-300 border-blue-300 dark:border-blue-800',
    bar: 'bg-blue-400',
    dot: 'bg-blue-400',
  },
  HEALTHY: {
    label: 'Healthy',
    badge: 'bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800',
    bar: 'bg-emerald-500',
    dot: 'bg-emerald-500',
  },
};

const ALL_RISKS = ['All', 'CRITICAL_OBSOLETE', 'HIGH_RISK', 'MODERATE', 'HEALTHY'];

function SkeletonCard() {
  return (
    <div className="p-4 sm:p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 animate-pulse">
      <div className="h-3 w-24 bg-slate-200 dark:bg-slate-700 rounded mb-2.5" />
      <div className="h-8 w-28 bg-slate-200 dark:bg-slate-700 rounded mb-2" />
      <div className="h-3 w-32 bg-slate-100 dark:bg-slate-800 rounded" />
    </div>
  );
}

function EmptyState({ title, message }) {
  return (
    <div className="py-12 px-4 text-center rounded-xl border border-dashed border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30">
      <div className="w-10 h-10 mx-auto mb-3 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
        <svg className="w-5 h-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
        </svg>
      </div>
      <h4 className="text-xs font-bold text-slate-700 dark:text-slate-300">{title}</h4>
      <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 max-w-sm mx-auto">{message}</p>
    </div>
  );
}

function BlueprintModal({ courseId, courseName, onClose }) {
  const [blueprint, setBlueprint] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let live = true;
    setBlueprint(null);
    setLoading(true);
    setError(null);
    api.getCourseModernizationBlueprint(courseId)
      .then(res => {
        if (!live) return;
        setBlueprint(res);
        setLoading(false);
      })
      .catch(err => {
        if (!live) return;
        setError(err.message || 'Failed to load blueprint');
        setLoading(false);
      });
    return () => { live = false; };
  }, [courseId]);

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800">
        <div className="flex items-center justify-between p-5 border-b border-slate-100 dark:border-slate-800 sticky top-0 bg-white dark:bg-slate-900 z-10">
          <div>
            <h2 className="font-bold text-slate-900 dark:text-white text-base leading-tight">Modernization Blueprint</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 truncate max-w-xs">{courseName}</p>
          </div>
          <button
            onClick={onClose}
            id="blueprint-modal-close"
            className="w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 flex items-center justify-center transition-colors cursor-pointer"
          >
            <svg className="w-4 h-4 text-slate-600 dark:text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-5">
          {loading && (
            <div className="space-y-4 animate-pulse">
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="p-4 rounded-xl border border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40">
                  <div className="h-3 w-20 bg-slate-200 dark:bg-slate-700 rounded mb-2" />
                  <div className="h-4 w-3/4 bg-slate-200 dark:bg-slate-700 rounded mb-2" />
                  <div className="h-3 w-full bg-slate-100 dark:bg-slate-800 rounded" />
                </div>
              ))}
            </div>
          )}
          {!loading && error && (
            <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-300 text-xs">{error}</div>
          )}
          {!loading && !error && blueprint && (
            <div className="space-y-5">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  { label: 'Health Score', value: `${blueprint.health_summary?.health_score ?? 0}/100`, color: 'text-slate-900 dark:text-white' },
                  { label: 'Placement Rate', value: `${blueprint.health_summary?.placement_rate ?? 0}%`, color: 'text-emerald-700 dark:text-emerald-400' },
                  { label: 'Modernity', value: `${blueprint.health_summary?.modernity_score ?? 0}/100`, color: 'text-teal-700 dark:text-teal-400' },
                  { label: 'Risk', value: RISK_META[blueprint.health_summary?.obsolescence_risk]?.label ?? blueprint.health_summary?.obsolescence_risk, color: blueprint.health_summary?.obsolescence_risk === 'HEALTHY' ? 'text-emerald-700 dark:text-emerald-400' : 'text-rose-700 dark:text-rose-400' },
                ].map(item => (
                  <div key={item.label} className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700 text-center">
                    <div className="text-[11px] text-slate-500 dark:text-slate-400 font-medium mb-1">{item.label}</div>
                    <div className={`text-sm font-black ${item.color}`}>{item.value}</div>
                  </div>
                ))}
              </div>
              <div className="p-3 rounded-xl bg-amber-50/60 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800/60 text-xs text-amber-800 dark:text-amber-300">
                <span className="font-bold">Oversupply Status: </span>{blueprint.health_summary?.oversupply_msg}
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-3">Action Plan</h3>
                <div className="space-y-3">
                  {(blueprint.modernization_blueprint?.action_plan || []).map(step => (
                    <div key={step.step} className="flex gap-3 p-4 rounded-xl border border-slate-100 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/30">
                      <div className="w-7 h-7 rounded-lg bg-slate-900 dark:bg-teal-600 text-white font-black text-xs flex items-center justify-center shrink-0 mt-0.5">{step.step}</div>
                      <div className="min-w-0">
                        <div className="text-[10px] font-mono font-semibold text-teal-600 dark:text-teal-400 mb-0.5">{step.phase}</div>
                        <div className="text-xs font-bold text-slate-900 dark:text-white leading-snug">{step.title}</div>
                        <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">{step.description}</div>
                        <div className="mt-1.5 text-[11px] font-semibold text-emerald-700 dark:text-emerald-400">{step.impact}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <h3 className="text-xs font-bold text-slate-900 dark:text-white mb-2">Equipment Requirements</h3>
                  <div className="space-y-2">
                    {(blueprint.modernization_blueprint?.equipment_requirements || []).slice(0, 3).map((eq, idx) => (
                      <div key={idx} className="p-2.5 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 text-xs">
                        <div className="font-semibold text-slate-800 dark:text-slate-200 leading-snug">{eq.item}</div>
                        <div className="text-slate-500 dark:text-slate-400 mt-0.5">{eq.units} units &middot; &#8377;{(eq.unit_cost_inr / 100000).toFixed(1)}L each</div>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <h3 className="text-xs font-bold text-slate-900 dark:text-white mb-2">Trainer Upskilling</h3>
                  <div className="space-y-2">
                    {(blueprint.modernization_blueprint?.trainer_upskilling || []).slice(0, 2).map((t, idx) => (
                      <div key={idx} className="p-2.5 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 text-xs">
                        <div className="font-semibold text-slate-800 dark:text-slate-200 leading-snug">{t.program}</div>
                        <div className="text-slate-500 dark:text-slate-400 mt-0.5">{t.duration} &middot; {t.certifying_body} &middot; {t.target_trainers} trainers</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700 flex items-center justify-between text-xs">
                <span className="text-slate-600 dark:text-slate-300">
                  <span className="font-bold text-slate-900 dark:text-white">Total Equipment Budget: </span>
                  &#8377;{((blueprint.modernization_blueprint?.total_equipment_budget_inr || 0) / 100000).toFixed(1)} Lakhs
                </span>
                <span className="font-semibold text-emerald-700 dark:text-emerald-400">{blueprint.modernization_blueprint?.target_placement_lift}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function CurriculumHub() {
  const [summary, setSummary] = useState(null);
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedBlueprint, setSelectedBlueprint] = useState(null);
  const [riskFilter, setRiskFilter] = useState('All');
  const [districtFilter, setDistrictFilter] = useState('All');
  const [categoryFilter, setCategoryFilter] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const requestIdRef = useRef(0);

  const fetchData = useCallback(() => {
    const currentRequestId = ++requestIdRef.current;
    setLoading(true);
    setError(null);
    Promise.allSettled([
      api.getCurriculumSummary(),
      api.getCurriculumAudit(),
    ]).then(([summaryRes, auditRes]) => {
      if (currentRequestId !== requestIdRef.current) return;
      if (summaryRes.status === 'fulfilled' && summaryRes.value?.status === 'success') {
        setSummary(summaryRes.value);
      } else {
        setSummary(null);
      }
      const raw = auditRes.status === 'fulfilled' ? auditRes.value : null;
      if (raw && raw.status !== 'error' && !raw.detail) {
        const arr = Array.isArray(raw?.courses) ? raw.courses : (Array.isArray(raw) ? raw : []);
        setCourses(arr);
      } else {
        const failureMessage = raw?.detail || raw?.message || auditRes.reason?.message || 'Failed to load curriculum audit data';
        setError(failureMessage);
      }
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    fetchData();
    return () => {
      requestIdRef.current++;
    };
  }, [fetchData]);

  const districts = useMemo(() => {
    const ds = [...new Set(courses.map(c => c.district).filter(Boolean))].sort();
    return ['All', ...ds];
  }, [courses]);

  const categories = useMemo(() => {
    const cs = [...new Set(courses.map(c => c.category).filter(Boolean))].sort();
    return ['All', ...cs];
  }, [courses]);

  const filtered = useMemo(() => courses.filter(c => {
    if (riskFilter !== 'All' && c.obsolescence_risk !== riskFilter) return false;
    if (districtFilter !== 'All' && c.district !== districtFilter) return false;
    if (categoryFilter !== 'All' && c.category !== categoryFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase();
      if (!c.course_name?.toLowerCase().includes(q) && !c.institute?.toLowerCase().includes(q)) return false;
    }
    return true;
  }), [courses, riskFilter, districtFilter, categoryFilter, searchQuery]);

  const riskCounts = useMemo(() => {
    const map = {};
    for (const c of courses) { map[c.obsolescence_risk] = (map[c.obsolescence_risk] || 0) + 1; }
    return map;
  }, [courses]);

  const computedAvgHealth = useMemo(() => {
    if (summary?.avg_health_score !== undefined && summary?.avg_health_score !== null) {
      return summary.avg_health_score;
    }
    if (courses.length === 0) return 0;
    const sum = courses.reduce((acc, c) => acc + (Number(c.health_score) || 0), 0);
    return Math.round((sum / courses.length) * 10) / 10;
  }, [summary, courses]);

  const computedTotalBudget = useMemo(() => {
    if (summary?.total_equipment_budget_estimate_inr !== undefined && summary?.total_equipment_budget_estimate_inr !== null) {
      return summary.total_equipment_budget_estimate_inr;
    }
    return courses.reduce((acc, c) => acc + (Number(c.total_equipment_budget_inr) || 0), 0);
  }, [summary, courses]);

  const computedOversupplyCount = useMemo(() => {
    if (summary?.oversupply_count !== undefined && summary?.oversupply_count !== null) {
      return summary.oversupply_count;
    }
    return courses.filter(c => (c.oversupply_status || '').includes('OVERSUPPLY')).length;
  }, [summary, courses]);

  return (
    <Layout>
      <div className="mb-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
                Curriculum Modernization Hub
              </h1>
              <span className="text-[10px] font-mono px-2 py-0.5 bg-teal-50 dark:bg-teal-950 text-teal-800 dark:text-teal-300 font-semibold rounded border border-teal-200 dark:border-teal-800">
                Intelligence Engine
              </span>
            </div>
            <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
              Course health analysis, obsolescence detection, and AI-grounded modernization blueprints for Maharashtra training institutes
            </p>
          </div>
          <button
            onClick={fetchData}
            id="curriculum-hub-refresh"
            className="px-4 py-2 bg-slate-900 dark:bg-slate-700 hover:bg-slate-800 dark:hover:bg-slate-600 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors cursor-pointer flex items-center gap-1.5 self-start sm:self-auto"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh Audit
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-8">
        {loading ? (
          Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)
        ) : (
          <>
            <StatCard title="Courses Audited" value={summary?.total_courses ?? courses.length} subtitle="Active vocational programs" icon="📋" />
            <StatCard title="Critical Obsolete" value={summary?.critical_obsolete_count ?? riskCounts.CRITICAL_OBSOLETE ?? 0} subtitle="Immediate revision needed" icon="🚨" color="rose" />
            <StatCard title="High Risk" value={summary?.high_risk_count ?? riskCounts.HIGH_RISK ?? 0} subtitle="Syllabus lagging industry" icon="⚠️" color="amber" />
            <StatCard title="Oversupply Flagged" value={computedOversupplyCount} subtitle="Seats exceeding demand" icon="📉" color="navy" />
            <StatCard title="Avg Health Score" value={`${computedAvgHealth}/100`} subtitle="State-wide course health" icon="💚" color="teal" />
            <StatCard title="Equipment Budget" value={`₹${(computedTotalBudget / 10000000).toFixed(1)}Cr`} subtitle="Est. modernization cost" icon="🏭" />
          </>
        )}
      </div>

      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs mb-6">
        <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex flex-col sm:flex-row gap-3 flex-wrap">
          <input
            type="text"
            id="curriculum-hub-search"
            placeholder="Search course or institute…"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="flex-1 min-w-[180px] px-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-500/30"
          />
          <select
            id="curriculum-hub-risk-filter"
            value={riskFilter}
            onChange={e => setRiskFilter(e.target.value)}
            className="px-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none"
          >
            {ALL_RISKS.map(r => (
              <option key={r} value={r}>
                {r === 'All' ? 'All Risk Levels' : (RISK_META[r]?.label || r)}{r !== 'All' && riskCounts[r] ? ` (${riskCounts[r]})` : ''}
              </option>
            ))}
          </select>
          <select
            id="curriculum-hub-district-filter"
            value={districtFilter}
            onChange={e => setDistrictFilter(e.target.value)}
            className="px-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none"
          >
            {districts.map(d => <option key={d} value={d}>{d === 'All' ? 'All Districts' : d}</option>)}
          </select>
          <select
            id="curriculum-hub-category-filter"
            value={categoryFilter}
            onChange={e => setCategoryFilter(e.target.value)}
            className="px-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none"
          >
            {categories.map(c => <option key={c} value={c}>{c === 'All' ? 'All Categories' : c}</option>)}
          </select>
          {filtered.length !== courses.length && (
            <button
              onClick={() => { setRiskFilter('All'); setDistrictFilter('All'); setCategoryFilter('All'); setSearchQuery(''); }}
              className="px-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors cursor-pointer"
            >
              Clear filters
            </button>
          )}
        </div>

        {loading && (
          <div className="p-6 space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-12 animate-pulse bg-slate-50 dark:bg-slate-800/40 rounded-lg" />
            ))}
          </div>
        )}

        {!loading && error && (
          <div className="p-6">
            <div className="p-4 rounded-xl border border-rose-200 dark:border-rose-800 bg-rose-50 dark:bg-rose-950/40 text-rose-800 dark:text-rose-300 text-xs">
              <span className="font-bold">Audit Unavailable: </span>{error}
              <button onClick={fetchData} className="ml-2 underline cursor-pointer">Retry</button>
            </div>
          </div>
        )}

        {!loading && !error && filtered.length === 0 && (
          <div className="p-6">
            <EmptyState title="No Courses Match" message="Adjust filters or verify that Supabase course records are populated." />
          </div>
        )}

        {!loading && !error && filtered.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 dark:text-slate-400 font-semibold border-b border-slate-200 dark:border-slate-700">
                <tr>
                  <th className="p-3 min-w-[180px]">Course / Trade</th>
                  <th className="p-3">District</th>
                  <th className="p-3 text-center">Health</th>
                  <th className="p-3 text-center">Modernity</th>
                  <th className="p-3 text-center">Placement</th>
                  <th className="p-3">Risk Level</th>
                  <th className="p-3">Oversupply</th>
                  <th className="p-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {filtered.map((course, idx) => {
                  const risk = RISK_META[course.obsolescence_risk] || RISK_META.MODERATE;
                  return (
                    <tr key={course.course_id || idx} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors">
                      <td className="p-3">
                        <div className="font-bold text-slate-900 dark:text-white leading-tight max-w-[200px]">{course.course_name}</div>
                        <div className="text-slate-500 dark:text-slate-400 text-[11px] mt-0.5 truncate max-w-[200px]">{course.institute}</div>
                      </td>
                      <td className="p-3 text-slate-600 dark:text-slate-300">{course.district}</td>
                      <td className="p-3 text-center">
                        <div className="flex items-center justify-center gap-1.5">
                          <div className="w-16 h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                            <div className={`h-full rounded-full ${risk.bar}`} style={{ width: `${Math.max(0, Math.min(100, Number(course.health_score) || 0))}%` }} />
                          </div>
                          <span className="font-mono font-bold text-slate-700 dark:text-slate-300">{course.health_score}</span>
                        </div>
                      </td>
                      <td className="p-3 text-center">
                        <div className="flex items-center justify-center gap-1.5">
                          <div className="w-16 h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                            <div className="h-full rounded-full bg-teal-500" style={{ width: `${Math.max(0, Math.min(100, Number(course.modernity_score) || 0))}%` }} />
                          </div>
                          <span className="font-mono font-bold text-slate-700 dark:text-slate-300">{course.modernity_score}</span>
                        </div>
                      </td>
                      <td className="p-3 text-center">
                        <span className={`font-bold ${course.placement_rate >= 70 ? 'text-emerald-700 dark:text-emerald-400' : course.placement_rate >= 50 ? 'text-amber-700 dark:text-amber-400' : 'text-rose-700 dark:text-rose-400'}`}>
                          {course.placement_rate}%
                        </span>
                      </td>
                      <td className="p-3">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border ${risk.badge}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${risk.dot}`} />
                          {risk.label}
                        </span>
                      </td>
                      <td className="p-3">
                        <span className={`text-[10px] font-mono font-semibold ${course.oversupply_status === 'OVERSUPPLY_CRITICAL' ? 'text-rose-700 dark:text-rose-400' : course.oversupply_status === 'MONITOR_OVERSUPPLY' ? 'text-amber-700 dark:text-amber-400' : 'text-slate-500 dark:text-slate-400'}`}>
                          {course.oversupply_status?.replace(/_/g, ' ') || 'BALANCED'}
                        </span>
                      </td>
                      <td className="p-3 text-right">
                        <button
                          id={`blueprint-btn-${course.course_id || idx}`}
                          onClick={() => setSelectedBlueprint({ id: course.course_id, name: course.course_name })}
                          className="px-3 py-1 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-[11px] font-bold shadow-xs transition-colors cursor-pointer"
                        >
                          Blueprint
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <div className="px-4 py-2 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-400 dark:text-slate-500">
              Showing {filtered.length} of {courses.length} courses
            </div>
          </div>
        )}
      </div>

      <div className="bg-slate-50 dark:bg-slate-900/50 rounded-xl border border-slate-100 dark:border-slate-800 p-4 text-[11px] text-slate-500 dark:text-slate-400">
        <span className="font-semibold text-slate-700 dark:text-slate-300">Data Provenance: </span>
        Course health scores are computed dynamically from active institutional placement records, employer demand signals, and multi-horizon skill forecasts. Blueprints reflect NSQF-aligned modernization paths, not guaranteed outcomes.
      </div>

      {selectedBlueprint && (
        <BlueprintModal
          courseId={selectedBlueprint.id}
          courseName={selectedBlueprint.name}
          onClose={() => setSelectedBlueprint(null)}
        />
      )}
    </Layout>
  );
}
