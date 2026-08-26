import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import Layout from '../components/Layout';
import StatCard from '../components/StatCard';
import SkillGapBar from '../components/SkillGapBar';
import { api } from '../services/api';

export default function DistrictPlan() {
  const { name } = useParams();
  const districtName = name || 'Pune';
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(false);
    api.getDistrictPlan(districtName)
      .then((res) => {
        setPlan(res);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }, [districtName]);

  if (loading) {
    return (
      <Layout>
        <div className="py-20 text-center text-slate-500 dark:text-slate-400">
          <div className="w-8 h-8 border-4 border-slate-900 dark:border-teal-500 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
          <p className="text-sm font-semibold">Loading {districtName} District Workforce Plan...</p>
        </div>
      </Layout>
    );
  }

  if (error || !plan) {
    return (
      <Layout>
        <div className="py-20 text-center">
          <p className="text-4xl font-black text-slate-200 dark:text-slate-800">⚠</p>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white mt-3">Unable to load {districtName} data</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">The backend may be offline. Start it to view district workforce plans.</p>
          <Link to="/government" className="inline-block mt-5 px-4 py-2 bg-slate-900 dark:bg-teal-600 text-white text-sm font-semibold rounded-lg hover:bg-slate-800 dark:hover:bg-teal-700 transition-colors">
            ← Back to Government Dashboard
          </Link>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      {/* Breadcrumb & Title */}
      <div className="mb-6">
        <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mb-2">
          <Link to="/government" className="hover:underline">Government Dashboard</Link>
          <span>/</span>
          <span className="font-semibold text-slate-900 dark:text-white">{districtName} District Training Plan</span>
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              {districtName} District Workforce & Training Plan
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Localized skill demand forecasting, institutional capacity, and training seat recommendations
            </p>
          </div>

          <Link
            to="/student/copilot"
            className="px-3.5 py-2 rounded-lg bg-teal-50 dark:bg-teal-950 text-teal-800 dark:text-teal-300 border border-teal-200 dark:border-teal-800 text-sm font-semibold hover:bg-teal-100 dark:hover:bg-teal-900 transition-colors self-start"
          >
            Ask Copilot about {districtName} →
          </Link>
        </div>
      </div>

      {/* District KPI Summary */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          title="Active Job Openings"
          value={plan?.total_jobs?.toString() || '0'}
          subtitle={`Local demand in ${districtName}`}
          icon="💼"
        />
        <StatCard
          title="Active ITIs / Institutes"
          value={plan?.total_courses?.toString() || '0'}
          subtitle="Certified training centres"
          icon="🏫"
          color="teal"
        />
        <StatCard
          title="Total Student Enrolment"
          value={plan?.total_enrolment?.toString() || '0'}
          subtitle="Annual seat capacity"
          icon="👥"
          color="amber"
        />
        <StatCard
          title="Top Demanded Role"
          value={plan?.top_roles?.[0]?.role || 'N/A'}
          subtitle={`${plan?.top_roles?.[0]?.count || 0} job postings`}
          icon="🎯"
          color="navy"
        />
      </div>

      {/* Grid: Top Demanded Roles & Industry Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Top Demanded Job Roles */}
        <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
          <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100 dark:border-slate-800">
            <div>
              <h3 className="font-bold text-slate-900 dark:text-white text-base">Top 5 Demanded Roles in {districtName}</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">Based on local job vacancy analysis</p>
            </div>
            <span className="text-xs font-semibold px-2 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded border border-slate-200 dark:border-slate-700">
              High Hiring
            </span>
          </div>

          <div className="space-y-3">
            {plan?.top_roles?.map((r, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700"
              >
                <div className="flex items-center gap-3">
                  <span className="w-7 h-7 rounded-lg bg-slate-900 dark:bg-teal-600 text-white font-bold text-xs flex items-center justify-center">
                    #{idx + 1}
                  </span>
                  <span className="font-bold text-slate-900 dark:text-white text-sm">{r.role}</span>
                </div>
                <span className="text-xs font-mono font-bold px-2 py-1 bg-white dark:bg-slate-900 rounded border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200">
                  {r.count} postings
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Local Industry Clusters */}
        <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
          <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100 dark:border-slate-800">
            <div>
              <h3 className="font-bold text-slate-900 dark:text-white text-base">Sector Breakdown</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">Primary industries driving hiring in {districtName}</p>
            </div>
            <span className="text-xs font-semibold px-2 py-0.5 bg-teal-50 dark:bg-teal-950 text-teal-800 dark:text-teal-300 rounded border border-teal-200 dark:border-teal-800">
              Cluster Data
            </span>
          </div>

          <div className="space-y-3">
            {plan?.industry_demand?.map((ind, idx) => (
              <div key={idx} className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700">
                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="font-bold text-slate-900 dark:text-white">{ind.industry}</span>
                  <span className="font-mono text-slate-600 dark:text-slate-400">{ind.count} jobs</span>
                </div>
                <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-slate-900 dark:bg-teal-400 h-1.5 rounded-full"
                    style={{ width: `${Math.min(100, (ind.count / (plan.total_jobs || 1)) * 100)}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Local Courses and Institutional Capacity */}
      <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs mb-8">
        <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100 dark:border-slate-800">
          <div>
            <h3 className="font-bold text-slate-900 dark:text-white text-base">Local Training Institutes & Course Health</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">Current institutional capacity in {districtName}</p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 dark:text-slate-400 font-semibold border-b border-slate-200 dark:border-slate-700">
              <tr>
                <th className="p-3">Course Name</th>
                <th className="p-3">Institute</th>
                <th className="p-3">Annual Enrolment</th>
                <th className="p-3 text-right">Placement Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {plan?.local_courses?.map((c, idx) => (
                <tr key={idx} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors">
                  <td className="p-3 font-bold text-slate-900 dark:text-white">{c.name}</td>
                  <td className="p-3 text-slate-600 dark:text-slate-300">{c.institute}</td>
                  <td className="p-3 font-mono text-slate-700 dark:text-slate-300">{c.enrolment} seats</td>
                  <td className="p-3 text-right font-bold">
                    <span className={`px-2 py-0.5 rounded-full text-[11px] ${
                      c.placement_rate >= 75 ? 'bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800' :
                      c.placement_rate >= 50 ? 'bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800' :
                      'bg-rose-50 dark:bg-rose-950 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800'
                    }`}>
                      {c.placement_rate}%
                    </span>
                  </td>
                </tr>
              ))}
              {(!plan?.local_courses || plan.local_courses.length === 0) && (
                <tr>
                  <td colSpan={4} className="p-6 text-center text-slate-400">
                    No registered courses directly in this district. Training spillover from adjacent district hubs.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* District Skill Gaps */}
      <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs mb-8">
        <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100 dark:border-slate-800">
          <div>
            <h3 className="font-bold text-slate-900 dark:text-white text-base">Key Skill Gaps in {districtName}</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">Skills where local industry demand exceeds current institutional output</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {plan?.skill_gaps?.slice(0, 4).map((g) => (
            <SkillGapBar
              key={g.skill_id}
              skillName={g.skill_name}
              category={g.category}
              demandPct={g.demand_pct}
              coveragePct={g.coverage_pct}
              gapPct={g.gap_pct}
              priority={g.priority}
              demandCount={g.demand_count}
            />
          ))}
        </div>
      </div>

      {/* Recommended Government Action */}
      <div className="bg-slate-900 dark:bg-slate-800 p-6 rounded-xl mb-8 text-white">
        <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-700">
          <div>
            <h3 className="font-bold text-white text-base">Recommended Government Action for {districtName}</h3>
            <p className="text-xs text-slate-400">Evidence-based training investment priorities derived from gap analysis</p>
          </div>
          <span className="text-[11px] font-semibold px-2.5 py-1 bg-teal-500/20 text-teal-300 rounded-full border border-teal-500/30">
            AI Recommended
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {(plan?.skill_gaps?.slice(0, 3) || []).map((g, idx) => (
            <div key={idx} className="p-4 rounded-lg bg-slate-800 dark:bg-slate-700/50 border border-slate-700 dark:border-slate-600">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-teal-400 uppercase">Priority {idx + 1}</span>
                <span className="text-[10px] font-mono bg-rose-500/20 text-rose-300 px-1.5 py-0.5 rounded border border-rose-500/30">
                  {g.gap_pct}% gap
                </span>
              </div>
              <h4 className="font-bold text-sm text-white mb-1">{g.skill_name}</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Allocate {Math.round((g.gap_pct / 100) * 200)} new training seats in {g.category || 'this domain'} courses across {districtName} ITIs.
                Current demand: {g.demand_count} employers actively hiring. Coverage: {g.coverage_pct}%.
              </p>
            </div>
          ))}
          {(!plan?.skill_gaps || plan.skill_gaps.length === 0) && (
            <div className="col-span-full text-center py-8 text-sm text-slate-400">
              No skill gap data available for recommendations.
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
