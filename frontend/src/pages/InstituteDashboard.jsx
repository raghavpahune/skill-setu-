import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import StatCard from '../components/StatCard';
import RecommendationCard from '../components/RecommendationCard';
import { api } from '../services/api';

const DEFAULT_COURSES = [
  {
    id: 'crs-001',
    name: 'Advanced Diploma in Artificial Intelligence & Machine Learning',
    description: 'Practical deep learning, Python, computer vision, and neural network applications.',
    institute: 'Government Polytechnic, Pune',
    district: 'Pune',
    enrolment_count: 60,
    placed_count: 54,
    placement_rate: 90,
    status: 'active'
  },
  {
    id: 'crs-002',
    name: 'Electric Vehicle Powertrain & Battery Systems Technician',
    description: 'Battery management systems, inverter diagnostics, EV powertrain assembly.',
    institute: 'Industrial Training Institute (ITI), Pimpri',
    district: 'Pune',
    enrolment_count: 45,
    placed_count: 40,
    placement_rate: 88,
    status: 'active'
  },
  {
    id: 'crs-003',
    name: 'Diploma in CNC & Precision Machining',
    description: 'Tool design, CNC turning, milling, and metrology standards.',
    institute: 'Government ITI, Chhatrapati Sambhajinagar',
    district: 'Chhatrapati Sambhajinagar',
    enrolment_count: 80,
    placed_count: 52,
    placement_rate: 65,
    status: 'needs_attention'
  },
  {
    id: 'crs-004',
    name: 'Conventional Manual Desktop Publishing & Printing',
    description: 'Offset printing and legacy desktop typography publishing.',
    institute: 'Government Technical High School, Solapur',
    district: 'Solapur',
    enrolment_count: 70,
    placed_count: 22,
    placement_rate: 31,
    status: 'review_oversupply'
  },
  {
    id: 'crs-005',
    name: 'Industrial Internet of Things (IIoT) & Automation',
    description: 'PLC programming, SCADA interfaces, sensor telemetry for Industry 4.0.',
    institute: 'Government Polytechnic, Nagpur',
    district: 'Nagpur',
    enrolment_count: 50,
    placed_count: 46,
    placement_rate: 92,
    status: 'active'
  },
];

const DEFAULT_RECOMMENDATIONS = [
  {
    recommendation: 'Incorporate Generative AI & Vector Search Modules into CS Curriculum',
    reason: '68% of tech job descriptions in Pune & Mumbai now require hands-on LLM/RAG capabilities.',
    confidence: 94,
    priority: 'HIGH',
    future_demand: 'high',
    trend: 'rising',
    gap_pct: 42,
    related_signals: ['Nasscom GenAI Talent Surge 2026', 'Maharashtra IT Policy 2024-29']
  },
  {
    recommendation: 'Restructure Conventional Printing Course into Digital Media & Web Design',
    reason: 'Placement rate has dropped to 31% due to rapid industry automation in Solapur & Kolhapur.',
    confidence: 89,
    priority: 'CRITICAL',
    future_demand: 'declining',
    trend: 'declining',
    gap_pct: 69,
    related_signals: ['MSInS Vocational Modernization Directive']
  }
];

export default function InstituteDashboard() {
  const [courses, setCourses] = useState(DEFAULT_COURSES);
  const [recommendations, setRecommendations] = useState(DEFAULT_RECOMMENDATIONS);
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.getCourses()
      .then((res) => {
        if (Array.isArray(res) && res.length > 0) setCourses(res);
      })
      .catch(() => {});

    api.getCourseRecommendations()
      .then((res) => {
        if (Array.isArray(res) && res.length > 0) setRecommendations(res);
      })
      .catch(() => {});
  }, []);

  const filteredCourses = courses.filter((c) => {
    if (filter === 'oversupply') return c.status === 'review_oversupply';
    if (filter === 'attention') return c.status === 'needs_attention';
    if (filter === 'healthy') return c.status === 'active';
    return true;
  });

  const oversupplyCount = courses.filter((c) => c.status === 'review_oversupply').length;
  const attentionCount = courses.filter((c) => c.status === 'needs_attention').length;
  const avgPlacement = courses.length > 0
    ? Math.round(courses.reduce((acc, c) => acc + (c.placement_rate || 0), 0) / courses.length)
    : 72;

  return (
    <Layout>
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              Training Institute & Curriculum Health Center
            </h1>
            <span className="text-[11px] font-mono px-2 py-0.5 bg-teal-50 dark:bg-teal-950 text-teal-800 dark:text-teal-300 font-semibold rounded border border-teal-200 dark:border-teal-800">
              MSBTE Aligned
            </span>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Audit vocational courses, detect obsolete syllabi, and align curriculum modules with real-time employer signals
          </p>
        </div>

        {oversupplyCount > 0 && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-300 text-xs font-bold shadow-xs self-start md:self-auto">
            <span>⚠️</span>
            <span>{oversupplyCount} Course flagged for curriculum restructuring</span>
          </div>
        )}
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          title="Monitored Courses"
          value={courses.length.toString()}
          subtitle="Across ITIs & Polytechnics"
          icon="📚"
        />
        <StatCard
          title="Average Placement"
          value={`${avgPlacement}%`}
          subtitle="State-wide certified trades"
          icon="🎓"
          color="teal"
        />
        <StatCard
          title="Curriculum Upgrades"
          value={recommendations.length.toString()}
          subtitle="High-priority revisions"
          icon="💡"
          color="amber"
        />
        <StatCard
          title="Oversupply Flags"
          value={oversupplyCount.toString()}
          subtitle="Requires syllabus pivot"
          icon="⚠️"
          color="rose"
        />
      </div>

      {/* Course Health & Obsolescence Review Table */}
      <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs mb-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-100 dark:border-slate-800">
          <div>
            <h3 className="font-bold text-slate-900 dark:text-white text-base">Course Health Matrix & Placement Audit</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">Live evaluation of student enrolment, industry placement rate, and obsolescence signals</p>
          </div>

          {/* Filter Pills */}
          <div className="flex items-center gap-1 self-start sm:self-auto text-xs bg-slate-100 dark:bg-slate-800 p-1 rounded-lg border border-slate-200 dark:border-slate-700">
            <button
              onClick={() => setFilter('all')}
              className={`px-3 py-1 rounded-md font-medium transition-all ${filter === 'all' ? 'bg-white dark:bg-slate-700 shadow-2xs font-bold text-slate-900 dark:text-white' : 'text-slate-600 dark:text-slate-400'}`}
            >
              All ({courses.length})
            </button>
            <button
              onClick={() => setFilter('oversupply')}
              className={`px-3 py-1 rounded-md font-medium transition-all ${filter === 'oversupply' ? 'bg-rose-600 text-white shadow-2xs font-bold' : 'text-rose-700 dark:text-rose-400'}`}
            >
              Oversupply ({oversupplyCount})
            </button>
            <button
              onClick={() => setFilter('healthy')}
              className={`px-3 py-1 rounded-md font-medium transition-all ${filter === 'healthy' ? 'bg-white dark:bg-slate-700 shadow-2xs font-bold text-slate-900 dark:text-white' : 'text-slate-600 dark:text-slate-400'}`}
            >
              Aligned
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 dark:text-slate-400 font-semibold border-b border-slate-200 dark:border-slate-700">
              <tr>
                <th className="p-3">Course & Focus</th>
                <th className="p-3">Institute & District</th>
                <th className="p-3">Enrolment</th>
                <th className="p-3">Placed</th>
                <th className="p-3">Placement Rate</th>
                <th className="p-3 text-right">Alignment Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {filteredCourses.map((c) => {
                const isOversupply = c.status === 'review_oversupply';
                return (
                  <tr
                    key={c.id}
                    className={`transition-colors ${isOversupply ? 'bg-rose-50/50 dark:bg-rose-950/20 hover:bg-rose-50 dark:hover:bg-rose-950/30' : 'hover:bg-slate-50/80 dark:hover:bg-slate-800/40'}`}
                  >
                    <td className="p-3 font-bold text-slate-900 dark:text-white max-w-xs">
                      <div className="flex items-center gap-1.5">
                        {isOversupply && <span className="text-rose-600 dark:text-rose-400 font-bold">⚠️</span>}
                        <span>{c.name}</span>
                      </div>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 font-normal mt-0.5 line-clamp-1">{c.description}</p>
                    </td>
                    <td className="p-3 text-slate-600 dark:text-slate-300">
                      <div className="font-medium text-slate-800 dark:text-slate-200">{c.institute}</div>
                      <div className="text-[11px] text-slate-400 font-mono">{c.district}</div>
                    </td>
                    <td className="p-3 font-mono font-semibold text-slate-700 dark:text-slate-300">{c.enrolment_count} seats</td>
                    <td className="p-3 font-mono text-slate-700 dark:text-slate-300">{c.placed_count}</td>
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        <span className={`font-bold font-mono ${
                          c.placement_rate >= 75 ? 'text-emerald-700 dark:text-emerald-400' :
                          c.placement_rate >= 50 ? 'text-amber-700 dark:text-amber-400' : 'text-rose-700 dark:text-rose-400'
                        }`}>
                          {c.placement_rate}%
                        </span>
                        <div className="w-16 bg-slate-200 dark:bg-slate-700 rounded-full h-1.5 overflow-hidden hidden sm:block">
                          <div
                            className={`h-1.5 rounded-full ${
                              c.placement_rate >= 75 ? 'bg-emerald-600 dark:bg-emerald-500' :
                              c.placement_rate >= 50 ? 'bg-amber-500' : 'bg-rose-500'
                            }`}
                            style={{ width: `${c.placement_rate}%` }}
                          ></div>
                        </div>
                      </div>
                    </td>
                    <td className="p-3 text-right">
                      {isOversupply ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-300 border border-rose-300 dark:border-rose-800">
                          LOW PLACEMENT / OVERSUPPLY
                        </span>
                      ) : c.status === 'needs_attention' ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-800">
                          CURRICULUM GAP
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800">
                          HIGH DEMAND ALIGNED
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Actionable Curriculum Recommendations */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-bold text-slate-900 dark:text-white text-lg">
              Actionable Curriculum Revisions for MSBTE / ITI Syllabus
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">Upgrade modular components based on regional employer demand gap signals</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {recommendations.map((rec, idx) => (
            <RecommendationCard key={idx} rec={rec} />
          ))}
        </div>
      </div>
    </Layout>
  );
}
