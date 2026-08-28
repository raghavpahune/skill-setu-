import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

const DEFAULT_DOMAINS = [
  { id: 'all', name: 'All Domains', icon: '🌐' },
  { id: 'ai_ml', name: 'AI / ML', icon: '🤖' },
  { id: 'data_science', name: 'Data Science', icon: '📊' },
  { id: 'cloud', name: 'Cloud Computing', icon: '☁️' },
  { id: 'cybersecurity', name: 'Cybersecurity', icon: '🛡️' },
  { id: 'robotics', name: 'Robotics', icon: '🦾' },
  { id: 'ev', name: 'Electric Vehicles', icon: '⚡' },
  { id: 'iot', name: 'IoT & Embedded', icon: '📡' },
];

export default function StudentAlertsFeed({ studentId, onOpenExplainability }) {
  const [selectedDomain, setSelectedDomain] = useState('all');
  const [domains, setDomains] = useState(DEFAULT_DOMAINS);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load alert domains
  useEffect(() => {
    api.getStudentAlertDomains()
      .then((res) => {
        if (res?.domains && Array.isArray(res.domains)) {
          setDomains([
            { id: 'all', name: 'All Domains', icon: '🌐' },
            ...res.domains.map((d) => ({
              id: d.id,
              name: d.name,
              icon: d.icon,
            })),
          ]);
        }
      })
      .catch(() => {
        // use default domains
      });
  }, []);

  // Fetch personalized industry alerts whenever domain or student changes
  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    const params = {};
    if (selectedDomain && selectedDomain !== 'all') {
      params.domain = selectedDomain;
    }
    if (studentId) {
      params.student_id = studentId;
    }

    api.getStudentIndustryAlerts(params)
      .then((res) => {
        if (!isMounted) return;
        if (res?.alerts && Array.isArray(res.alerts)) {
          setAlerts(res.alerts);
        } else {
          setAlerts([]);
        }
        setLoading(false);
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err.message || 'Failed to load industry alerts feed');
        setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [selectedDomain, studentId]);

  return (
    <div className="space-y-4">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-100 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-slate-900 dark:text-white text-base sm:text-lg">
              Personalized Industry & Technology Alerts
            </h3>
            <span className="text-[10px] font-mono font-bold px-2 py-0.5 bg-teal-50 dark:bg-teal-950 text-teal-800 dark:text-teal-300 rounded border border-teal-200 dark:border-teal-800">
              Section 19
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Select high-growth technology domains to monitor live industry shifts, hiring demand surge, and targeted next steps.
          </p>
        </div>
      </div>

      {/* Domain Chip Selector */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1.5 scrollbar-thin">
        {domains.map((dom) => {
          const isSelected = selectedDomain === dom.id;
          return (
            <button
              key={dom.id}
              onClick={() => setSelectedDomain(dom.id)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold shrink-0 transition-all cursor-pointer ${
                isSelected
                  ? 'bg-slate-900 dark:bg-teal-600 text-white shadow-xs'
                  : 'bg-white dark:bg-slate-800/80 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800'
              }`}
            >
              <span>{dom.icon}</span>
              <span>{dom.name}</span>
            </button>
          );
        })}
      </div>

      {/* Alert Feed Content */}
      {loading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 animate-pulse">
          <div className="h-64 rounded-xl bg-slate-100 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800"></div>
          <div className="h-64 rounded-xl bg-slate-100 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800"></div>
        </div>
      ) : error ? (
        <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-xs text-rose-800 dark:text-rose-300 flex items-center justify-between">
          <span>Failed to load industry alerts: {error}</span>
          <button
            onClick={() => setSelectedDomain('all')}
            className="px-2 py-1 bg-white dark:bg-slate-900 border border-rose-300 rounded font-bold"
          >
            Reset Filters
          </button>
        </div>
      ) : alerts.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {alerts.map((alert) => {
            const sig = alert.primary_signal;
            const impact = alert.career_impact;
            const demand = alert.job_demand_signal;

            return (
              <div
                key={alert.domain_id}
                className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-xs flex flex-col justify-between hover:border-teal-300 dark:hover:border-teal-700 transition-all space-y-4"
              >
                <div>
                  {/* Card Header */}
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xl p-1.5 bg-slate-100 dark:bg-slate-800 rounded-lg">
                        {alert.domain_icon}
                      </span>
                      <div>
                        <span className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-wider block">
                          {alert.domain_name} • {sig.source}
                        </span>
                        <h4 className="font-bold text-slate-900 dark:text-white text-sm leading-snug">
                          {sig.title}
                        </h4>
                      </div>
                    </div>

                    <span
                      className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full shrink-0 border ${
                        impact.level === 'CRITICAL'
                          ? 'bg-rose-50 dark:bg-rose-950 text-rose-700 dark:text-rose-300 border-rose-200 dark:border-rose-800'
                          : impact.level === 'HIGH'
                          ? 'bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800'
                          : 'bg-teal-50 dark:bg-teal-950 text-teal-700 dark:text-teal-300 border-teal-200 dark:border-teal-800'
                      }`}
                    >
                      Impact: {impact.level} ({impact.score_out_of_10}/10)
                    </span>
                  </div>

                  {/* Summary */}
                  <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed mb-3">
                    {sig.summary}
                  </p>

                  {/* Job Demand Signal Bar */}
                  <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs mb-3">
                    <div>
                      <span className="text-[10px] text-slate-400 font-mono block">Labour Market Hiring</span>
                      <span className="font-bold text-slate-900 dark:text-white">
                        {demand.active_vacancies_count} Vacancies ({demand.demand_share_pct}% state share)
                      </span>
                    </div>
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                      {demand.hiring_trend}
                    </span>
                  </div>

                  {/* Skills Student Should Strengthen */}
                  {alert.skills_to_strengthen.length > 0 && (
                    <div className="mb-3">
                      <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider block mb-1.5">
                        ⚡ Recommended Competencies to Strengthen:
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {alert.skills_to_strengthen.map((sk) => (
                          <button
                            key={sk.skill_id}
                            onClick={() => onOpenExplainability && onOpenExplainability(sk.skill_id, sk.name)}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 transition-colors cursor-pointer"
                            title="Click to view full 5-dimension explainability justification"
                          >
                            <span>{sk.name}</span>
                            <span className="text-[10px] text-indigo-500 font-mono font-normal">
                              (Gap: {sk.gap_pct}%)
                            </span>
                            <span className="text-[9px] text-indigo-400 font-bold">ⓘ</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Actionable Next Steps */}
                  <div className="space-y-1 pt-1 border-t border-slate-100 dark:border-slate-800">
                    <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider block mb-1">
                      🎯 Actionable Next Steps:
                    </span>
                    {alert.actionable_next_steps.map((step, idx) => (
                      <div key={idx} className="flex items-start gap-1.5 text-xs text-slate-600 dark:text-slate-300">
                        <span className="text-teal-600 dark:text-teal-400 font-bold">✓</span>
                        <span className="leading-snug">{step}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Card Footer: Related Courses & Explain Trigger */}
                <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs">
                  {alert.related_courses.length > 0 ? (
                    <span className="text-[11px] text-slate-500 truncate max-w-[65%]">
                      Related: <strong>{alert.related_courses[0].name}</strong> ({alert.related_courses[0].district})
                    </span>
                  ) : (
                    <span className="text-[11px] text-slate-400 font-mono">
                      Statewide Technology Shift
                    </span>
                  )}

                  {alert.affected_skills.length > 0 && (
                    <button
                      onClick={() => onOpenExplainability && onOpenExplainability(alert.affected_skills[0].skill_id, alert.affected_skills[0].name)}
                      className="text-xs font-bold text-teal-700 dark:text-teal-300 hover:text-teal-900 dark:hover:text-teal-100 cursor-pointer"
                    >
                      Why Learn {alert.affected_skills[0].name}? →
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="p-8 text-center bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-500">
          <p className="text-sm font-semibold">No active alerts for this domain.</p>
          <button
            onClick={() => setSelectedDomain('all')}
            className="mt-2 text-xs font-bold text-teal-600 dark:text-teal-400 hover:underline"
          >
            View all technology signals
          </button>
        </div>
      )}
    </div>
  );
}
