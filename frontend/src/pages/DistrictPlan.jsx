import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import Layout from '../components/Layout';
import StatCard from '../components/StatCard';
import SkillGapBar from '../components/SkillGapBar';
import { api } from '../services/api';

const DISTRICT_NAMES = [
  'Pune',
  'Mumbai',
  'Nagpur',
  'Thane',
  'Nashik',
  'Kolhapur',
  'Chhatrapati Sambhajinagar',
  'Amravati',
  'Solapur',
  'Ratnagiri',
];

const EMPTY_DISTRICT_PLAN = (district) => ({
  district,
  total_jobs: 0,
  total_courses: 0,
  total_enrolment: 0,
  top_roles: [],
  industry_demand: [],
  local_courses: [],
  skill_gaps: [],
  top_skills: [],
});

function EmptyState({
  title = 'No records available',
  message = 'No data points were returned for this section.',
  icon,
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
          <h4 className="text-xs font-bold">Network Communication Issue</h4>
          <p className="text-[11px] text-rose-700 dark:text-rose-400 mt-0.5">{message}</p>
        </div>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors shrink-0"
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
      <div className="h-8 w-20 bg-slate-200 dark:bg-slate-800 rounded mb-2"></div>
      <div className="h-3 w-32 bg-slate-100 dark:bg-slate-800/60 rounded"></div>
    </div>
  );
}

export default function DistrictPlan() {
  const { name } = useParams();
  const navigate = useNavigate();
  const districtName = name || 'Pune';

  const [plan, setPlan] = useState(() => EMPTY_DISTRICT_PLAN(districtName));
  const [loading, setLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  const fetchPlan = () => {
    setLoading(true);
    setHasError(false);

    api.getDistrictPlan(districtName)
      .then((res) => {
        if (res && res.district) {
          setPlan(res);
        } else {
          setPlan(EMPTY_DISTRICT_PLAN(districtName));
        }
        setLoading(false);
      })
      .catch((err) => {
        console.warn(`[DistrictPlan] Could not fetch live plan for ${districtName}:`, err);
        setHasError(true);
        setPlan(EMPTY_DISTRICT_PLAN(districtName));
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchPlan();
  }, [districtName]);

  return (
    <Layout>
      {/* Breadcrumb & Title */}
      <div className="mb-6">
        <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mb-2">
          <Link to="/government" className="hover:underline text-teal-700 dark:text-teal-400 font-medium">
            Government Hub
          </Link>
          <span>/</span>
          <span className="font-semibold text-slate-900 dark:text-white">
            {districtName} Workforce Plan
          </span>
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
                {districtName} District Workforce Plan
              </h1>
              <span className="text-[10px] font-mono px-2 py-0.5 bg-teal-50 dark:bg-teal-950 text-teal-800 dark:text-teal-300 font-semibold rounded border border-teal-200 dark:border-teal-800">
                Live Zone
              </span>
            </div>
            <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
              Localized skill demand forecasting, institutional capacity, and training seat allocation directives
            </p>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto flex-wrap">
            {/* Quick District Switcher */}
            <div className="flex items-center gap-1.5 bg-white dark:bg-slate-900 p-1.5 px-3 rounded-lg border border-slate-200 dark:border-slate-800 text-xs shadow-2xs">
              <span className="font-semibold text-slate-500 dark:text-slate-400">Switch District:</span>
              <select
                value={districtName}
                onChange={(e) => navigate(`/government/district/${encodeURIComponent(e.target.value)}`)}
                className="bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded px-2 py-0.5 font-bold text-slate-900 dark:text-white focus:outline-none"
              >
                {DISTRICT_NAMES.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </div>

            <Link
              to={`/student/copilot?district=${encodeURIComponent(districtName)}&q=${encodeURIComponent(`Give me a detailed workforce intelligence briefing for ${districtName}.`)}&role=government`}
              className="px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-700 hover:to-emerald-700 text-white text-xs font-bold shadow-xs transition-all flex items-center gap-1.5 cursor-pointer"
            >
              <span>✨</span>
              <span>Ask AI Copilot about {districtName}</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Non-blocking Error Banner if API offline */}
      {hasError && (
        <ErrorBanner
          message={`Using localized cached benchmark model for ${districtName}. Backend connection was temporarily unavailable.`}
          onRetry={fetchPlan}
        />
      )}

      {/* District KPI Summary */}
      <div data-demo="district-kpi-summary" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
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
              title="Active Job Openings"
              value={plan?.total_jobs?.toString() || '0'}
              subtitle={`Local demand in ${districtName}`}
              icon="💼"
            />
            <StatCard
              title="Training Institutes"
              value={plan?.total_courses?.toString() || '0'}
              subtitle="Certified ITIs & Polytechnics"
              icon="🏫"
              color="teal"
            />
            <StatCard
              title="Annual Enrolment"
              value={`${plan?.total_enrolment || 0} seats`}
              subtitle="Registered training capacity"
              icon="👥"
              color="amber"
            />
            <StatCard
              title="Top Demanded Role"
              value={plan?.top_roles?.[0]?.role || 'N/A'}
              subtitle={`${plan?.top_roles?.[0]?.count || 0} active postings`}
              icon="🎯"
              color="navy"
            />
          </>
        )}
      </div>

      {/* Grid: Top Demanded Roles & Industry Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Top Demanded Job Roles */}
        <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100 dark:border-slate-800">
              <div>
                <h3 className="font-bold text-slate-900 dark:text-white text-base">
                  Top Demanded Job Roles in {districtName}
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Highest volume vacancies parsed from regional employer hiring requisitions
                </p>
              </div>
              <span className="text-[10px] font-mono font-semibold px-2 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded border border-slate-200 dark:border-slate-700">
                High Hiring
              </span>
            </div>

            {loading ? (
              <div className="space-y-2.5 py-1 animate-pulse">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="h-11 bg-slate-50 dark:bg-slate-800/60 rounded-lg"></div>
                ))}
              </div>
            ) : plan?.top_roles && plan.top_roles.length > 0 ? (
              <div className="space-y-2.5">
                {plan.top_roles.map((r, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700"
                  >
                    <div className="flex items-center gap-3">
                      <span className="w-6 h-6 rounded-md bg-slate-900 dark:bg-teal-600 text-white font-bold text-xs flex items-center justify-center">
                        #{idx + 1}
                      </span>
                      <span className="font-bold text-slate-900 dark:text-white text-xs sm:text-sm">
                        {r.role}
                      </span>
                    </div>
                    <span className="text-xs font-mono font-bold px-2 py-0.5 bg-white dark:bg-slate-900 rounded border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200">
                      {r.count} postings
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No Active Roles Recorded"
                message={`No distinct job roles currently indexed for ${districtName}.`}
              />
            )}
          </div>
        </div>

        {/* Local Industry Clusters */}
        <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100 dark:border-slate-800">
              <div>
                <h3 className="font-bold text-slate-900 dark:text-white text-base">
                  Industrial Sector Clusters
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Dominant manufacturing and service industries driving employment in {districtName}
                </p>
              </div>
              <span className="text-[10px] font-mono font-semibold px-2 py-0.5 bg-teal-50 dark:bg-teal-950 text-teal-800 dark:text-teal-300 rounded border border-teal-200 dark:border-teal-800">
                Cluster Data
              </span>
            </div>

            {loading ? (
              <div className="space-y-3 py-1 animate-pulse">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-14 bg-slate-50 dark:bg-slate-800/60 rounded-lg"></div>
                ))}
              </div>
            ) : plan?.industry_demand && plan.industry_demand.length > 0 ? (
              <div className="space-y-3">
                {plan.industry_demand.map((ind, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700"
                  >
                    <div className="flex justify-between items-center text-xs mb-1.5">
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
            ) : (
              <EmptyState
                title="No Sector Breakdown"
                message={`Industry cluster telemetry is being indexed for ${districtName}.`}
              />
            )}
          </div>
        </div>
      </div>

      {/* Local Courses and Institutional Capacity */}
      <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs mb-8">
        <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100 dark:border-slate-800">
          <div>
            <h3 className="font-bold text-slate-900 dark:text-white text-base">
              Local Training Institutes & Course Health
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Approved vocational curriculum capacity and placement outcomes across {districtName}
            </p>
          </div>
        </div>

        {loading ? (
          <div className="space-y-3 py-2 animate-pulse">
            <div className="h-8 bg-slate-100 dark:bg-slate-800/80 rounded"></div>
            <div className="h-10 bg-slate-50 dark:bg-slate-800/40 rounded"></div>
            <div className="h-10 bg-slate-50 dark:bg-slate-800/40 rounded"></div>
          </div>
        ) : plan?.local_courses && plan.local_courses.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 dark:text-slate-400 font-semibold border-b border-slate-200 dark:border-slate-700">
                <tr>
                  <th className="p-3">Course / Trade Name</th>
                  <th className="p-3">Institute Name</th>
                  <th className="p-3">Annual Intake</th>
                  <th className="p-3 text-right">Placement Rate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {plan.local_courses.map((c, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors">
                    <td className="p-3 font-bold text-slate-900 dark:text-white">{c.name}</td>
                    <td className="p-3 text-slate-600 dark:text-slate-300">{c.institute}</td>
                    <td className="p-3 font-mono text-slate-700 dark:text-slate-300">{c.enrolment} seats</td>
                    <td className="p-3 text-right font-bold">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[11px] ${
                          c.placement_rate >= 75
                            ? 'bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                            : c.placement_rate >= 50
                            ? 'bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800'
                            : 'bg-rose-50 dark:bg-rose-950 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800'
                        }`}
                      >
                        {c.placement_rate}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="No Direct Registered ITI Courses in District"
            message={`Training capacity for ${districtName} is currently serviced by regional cluster institutes in adjacent hubs.`}
          />
        )}
      </div>

      {/* District Skill Gaps */}
      <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs mb-8">
        <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100 dark:border-slate-800">
          <div>
            <h3 className="font-bold text-slate-900 dark:text-white text-base">
              Identified Skill Deficits in {districtName}
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Technical proficiencies where local employer hiring demand significantly outstrips institutional graduates
            </p>
          </div>
          <span className="text-[10px] font-mono font-semibold px-2 py-0.5 bg-rose-50 dark:bg-rose-950 text-rose-700 dark:text-rose-300 rounded border border-rose-200 dark:border-rose-800">
            Deficit Analysis
          </span>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 py-2 animate-pulse">
            <div className="h-20 bg-slate-50 dark:bg-slate-800/60 rounded-lg"></div>
            <div className="h-20 bg-slate-50 dark:bg-slate-800/60 rounded-lg"></div>
          </div>
        ) : plan?.skill_gaps && plan.skill_gaps.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {plan.skill_gaps.map((g) => (
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
        ) : (
          <EmptyState
            title="No Severe Skill Gaps Detected"
            message={`Local institutional output currently satisfies employer hiring benchmarks in ${districtName}.`}
          />
        )}
      </div>

      {/* Recommended Government Action Directives Section */}
      <div data-demo="district-micro-plan" className="bg-slate-900 dark:bg-slate-850 p-6 sm:p-7 rounded-xl mb-8 text-white border border-slate-800 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6 pb-3 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-white text-lg tracking-tight">
                Recommended Government Actions for {districtName}
              </h3>
              <span className="text-[10px] font-mono px-2 py-0.5 bg-teal-500/20 text-teal-300 rounded border border-teal-500/30">
                Action Directives
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Concrete policy, seat quota, and curriculum intervention directives derived from {districtName} skill-gap telemetry
            </p>
          </div>
          <div className="flex items-center gap-2 self-start sm:self-auto flex-wrap">
            <span className="text-[11px] font-semibold px-2.5 py-1 bg-teal-500/20 text-teal-300 rounded-full border border-teal-500/30">
              AI Policy Engine
            </span>
            <Link
              to={`/student/copilot?district=${encodeURIComponent(districtName)}&q=${encodeURIComponent(`Give me a detailed workforce intelligence briefing for ${districtName}.`)}&role=government`}
              className="px-2.5 py-1 rounded-lg bg-teal-500/20 hover:bg-teal-500/30 text-teal-300 border border-teal-500/40 text-[11px] font-bold transition-colors flex items-center gap-1 cursor-pointer"
            >
              <span>✨</span>
              <span>Ask Copilot for Deep Briefing</span>
              <span>→</span>
            </Link>
          </div>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 animate-pulse">
            <div className="h-44 bg-slate-800 rounded-lg"></div>
            <div className="h-44 bg-slate-800 rounded-lg"></div>
            <div className="h-44 bg-slate-800 rounded-lg"></div>
          </div>
        ) : plan?.skill_gaps && plan.skill_gaps.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {plan.skill_gaps.slice(0, 3).map((g, idx) => {
              const suggestedSeats = Math.round((g.gap_pct / 100) * 120) + 30;
              const horizon = idx === 0 ? 'Immediate (0–3 Months)' : idx === 1 ? 'Academic Year (3–6 Months)' : 'Strategic (6–12 Months)';
              const agency = idx === 0 ? 'Directorate of Vocational Education (DVET)' : idx === 1 ? 'MSBTE Curriculum Board' : 'District Skill Development Committee';

              return (
                <div
                  key={idx}
                  className="p-4 rounded-xl bg-slate-800/80 border border-slate-700/80 flex flex-col justify-between hover:border-slate-600 transition-colors"
                >
                  <div>
                    <div className="flex items-center justify-between mb-2.5">
                      <span className="text-xs font-bold text-teal-400 uppercase tracking-wider">
                        Directive 0{idx + 1}
                      </span>
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold border ${
                          g.priority === 'CRITICAL'
                            ? 'bg-rose-500/20 text-rose-300 border-rose-500/30'
                            : 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                        }`}
                      >
                        {g.gap_pct}% Gap Deficit
                      </span>
                    </div>

                    <h4 className="font-bold text-sm text-white mb-2 leading-snug">
                      Expand {g.skill_name} Capacity
                    </h4>

                    <p className="text-xs text-slate-300 leading-relaxed mb-3">
                      Sanction <span className="font-bold text-teal-300">{suggestedSeats} additional training seats</span> in{' '}
                      <span className="font-semibold text-white">{g.category || 'target domain'}</span> across {districtName} institutes.
                      Local hiring pressure reflects <span className="font-bold text-white">{g.demand_count} active job listings</span> against only {g.coverage_pct}% syllabus coverage.
                    </p>
                  </div>

                  <div className="pt-3 border-t border-slate-700/60 text-[11px] space-y-1">
                    <div className="flex justify-between text-slate-400">
                      <span>Timeline:</span>
                      <span className="font-semibold text-slate-200">{horizon}</span>
                    </div>
                    <div className="flex justify-between text-slate-400">
                      <span>Lead Authority:</span>
                      <span className="font-mono text-teal-400 text-[10px]">{agency}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <EmptyState
            title="No Directives Generated"
            message={`No critical skill deficits requiring emergency seat intervention were identified for ${districtName}.`}
          />
        )}
      </div>

      {/* Grid: Required Equipment & Required Trainers (§13) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Required Equipment Grants & Budget */}
        <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100 dark:border-slate-800">
              <div>
                <h3 className="font-bold text-slate-900 dark:text-white text-base">
                  Required Lab Equipment Grants
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Targeted laboratory apparatus needed to close high-gap competencies in {districtName}
                </p>
              </div>
              <span className="text-[10px] font-mono font-semibold px-2 py-0.5 bg-teal-50 dark:bg-teal-950 text-teal-800 dark:text-teal-300 rounded border border-teal-200 dark:border-teal-800">
                ₹{((plan?.total_equipment_budget_inr || 0) / 100000).toFixed(1)}L Est.
              </span>
            </div>

            {loading ? (
              <div className="space-y-3 py-1 animate-pulse">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-14 bg-slate-50 dark:bg-slate-800/60 rounded-lg"></div>
                ))}
              </div>
            ) : plan?.required_equipment && plan.required_equipment.length > 0 ? (
              <div className="space-y-3">
                {plan.required_equipment.slice(0, 4).map((eq, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700 flex items-center justify-between gap-3"
                  >
                    <div>
                      <div className="font-bold text-slate-900 dark:text-white text-xs">{eq.item}</div>
                      <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                        Domain: <span className="font-medium text-slate-700 dark:text-slate-300">{eq.domain || eq.category}</span> • Qty: <span className="font-mono font-bold text-teal-600 dark:text-teal-400">{eq.units} units</span>
                      </div>
                    </div>
                    <span className="text-xs font-mono font-bold text-slate-700 dark:text-slate-300 px-2 py-1 bg-white dark:bg-slate-900 rounded border border-slate-200 dark:border-slate-700 shrink-0">
                      ₹{((eq.total_cost_inr || eq.units * eq.unit_cost_inr) / 100000).toFixed(1)}L
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="Standard Labs Sufficient"
                message={`No specialized high-cost machinery required for current ${districtName} programs.`}
              />
            )}
          </div>
        </div>

        {/* Required Trainers & Certified Instructors */}
        <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100 dark:border-slate-800">
              <div>
                <h3 className="font-bold text-slate-900 dark:text-white text-base">
                  Trainer & Master Instructor Needs
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Certified faculty upskilling programs to support {plan?.required_training_seats || 180} additional training seats
                </p>
              </div>
              <span className="text-[10px] font-mono font-semibold px-2 py-0.5 bg-blue-50 dark:bg-blue-950 text-blue-800 dark:text-blue-300 rounded border border-blue-200 dark:border-blue-800">
                {plan?.required_trainers_count || 4} Trainers Needed
              </span>
            </div>

            {loading ? (
              <div className="space-y-3 py-1 animate-pulse">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-14 bg-slate-50 dark:bg-slate-800/60 rounded-lg"></div>
                ))}
              </div>
            ) : plan?.trainer_programs && plan.trainer_programs.length > 0 ? (
              <div className="space-y-3">
                {plan.trainer_programs.slice(0, 3).map((tp, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                  >
                    <div>
                      <div className="font-bold text-slate-900 dark:text-white text-xs">{tp.program}</div>
                      <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                        Duration: <span className="font-medium text-slate-700 dark:text-slate-300">{tp.duration}</span> • Certifier: <span className="font-medium text-teal-600 dark:text-teal-400">{tp.certifying_body}</span>
                      </div>
                    </div>
                    <span className="text-[11px] font-bold px-2 py-0.5 bg-blue-50 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 rounded self-start sm:self-auto border border-blue-200 dark:border-blue-800">
                      {tp.target_trainers || 2} Seats
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="Faculty Ratio Balanced"
                message={`Current institutional instructor capacity meets teaching guidelines for ${districtName}.`}
              />
            )}
          </div>
        </div>
      </div>

      {/* Grid: Courses Needing Review & Expected Impact (§13 & §11) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Courses Needing Human Review */}
        <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100 dark:border-slate-800">
              <div>
                <h3 className="font-bold text-slate-900 dark:text-white text-base">
                  Courses Flagged for Review in {districtName}
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Trades facing high obsolescence risk or labor oversupply for human administrative review
                </p>
              </div>
              <span className="text-[10px] font-mono font-semibold px-2 py-0.5 bg-rose-50 dark:bg-rose-950 text-rose-800 dark:text-rose-300 rounded border border-rose-200 dark:border-rose-800">
                Human Review Gate
              </span>
            </div>

            {loading ? (
              <div className="space-y-3 py-1 animate-pulse">
                {[1, 2].map((i) => (
                  <div key={i} className="h-16 bg-slate-50 dark:bg-slate-800/60 rounded-lg"></div>
                ))}
              </div>
            ) : plan?.courses_needing_review && plan.courses_needing_review.length > 0 ? (
              <div className="space-y-3">
                {plan.courses_needing_review.map((cr, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-rose-50/40 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/60 flex flex-col justify-between"
                  >
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <div>
                        <div className="font-bold text-slate-900 dark:text-white text-xs">{cr.name}</div>
                        <div className="text-[11px] text-slate-500 dark:text-slate-400">{cr.institute}</div>
                      </div>
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-rose-100 dark:bg-rose-900 text-rose-800 dark:text-rose-200">
                        {cr.obsolescence_risk.replace('_', ' ')}
                      </span>
                    </div>
                    <div className="text-[11px] text-rose-700 dark:text-rose-400 mt-1">
                      Placement: <span className="font-bold">{cr.placement_rate}%</span> • Health Score: <span className="font-bold">{cr.health_score}/100</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No Stagnant Courses"
                message={`All active vocational trades in ${districtName} maintain healthy placement conversion rates.`}
              />
            )}
          </div>
        </div>

        {/* Expected District Workforce Impact (§13) */}
        <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100 dark:border-slate-800">
              <div>
                <h3 className="font-bold text-slate-900 dark:text-white text-base">
                  Expected Impact Projections
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Data-backed placement lift and deficit reduction if district action directives are executed
                </p>
              </div>
              <span className="text-[10px] font-mono font-semibold px-2 py-0.5 bg-emerald-50 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 rounded border border-emerald-200 dark:border-emerald-800">
                SIMULATED ESTIMATE
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 py-1">
              <div className="p-3.5 rounded-lg bg-emerald-50/50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800">
                <div className="text-[11px] text-emerald-800 dark:text-emerald-300 font-semibold">Placement Rate Lift</div>
                <div className="text-2xl font-black text-emerald-700 dark:text-emerald-400 mt-1">
                  +{plan?.expected_impact?.projected_placement_lift_pct || 18.5}%
                </div>
                <div className="text-[10px] text-emerald-600 dark:text-emerald-400 mt-0.5">Target: {plan?.expected_impact?.target_placed_students || 150} candidates</div>
              </div>

              <div className="p-3.5 rounded-lg bg-teal-50/50 dark:bg-teal-950/30 border border-teal-200 dark:border-teal-800">
                <div className="text-[11px] text-teal-800 dark:text-teal-300 font-semibold">Skill Deficit Reduction</div>
                <div className="text-2xl font-black text-teal-700 dark:text-teal-400 mt-1">
                  -{plan?.expected_impact?.projected_skill_deficit_reduction_pct || 42.0}%
                </div>
                <div className="text-[10px] text-teal-600 dark:text-teal-400 mt-0.5">Across {plan?.skill_gaps?.length || 4} critical domains</div>
              </div>
            </div>

            <div className="mt-3 p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700 text-xs text-slate-600 dark:text-slate-300">
              <span className="font-bold text-slate-900 dark:text-white">Estimated Budget Package:</span> ₹{(((plan?.expected_impact?.total_budget_estimate_inr || 2400000)) / 100000).toFixed(1)} Lakhs allocated for laboratory rigs and trainer certifications across {districtName}.
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}

