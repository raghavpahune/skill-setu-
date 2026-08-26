import React from 'react';

export default function SignalCard({ signal }) {
  const impactStyles = {
    critical: {
      bg: 'bg-rose-100 dark:bg-rose-950/60',
      text: 'text-rose-800 dark:text-rose-300',
      border: 'border-rose-200 dark:border-rose-800',
    },
    high: {
      bg: 'bg-amber-100 dark:bg-amber-950/60',
      text: 'text-amber-800 dark:text-amber-300',
      border: 'border-amber-200 dark:border-amber-800',
    },
    medium: {
      bg: 'bg-blue-100 dark:bg-blue-950/60',
      text: 'text-blue-800 dark:text-blue-300',
      border: 'border-blue-200 dark:border-blue-800',
    },
    low: {
      bg: 'bg-slate-100 dark:bg-slate-800',
      text: 'text-slate-800 dark:text-slate-300',
      border: 'border-slate-200 dark:border-slate-700',
    },
  };

  const impact = impactStyles[signal.impact_level] || impactStyles.medium;

  return (
    <div className="p-5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs hover:shadow-sm transition-all">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-sm shrink-0">
            📡
          </div>
          <div>
            <h4 className="font-bold text-slate-900 dark:text-white text-sm">{signal.title}</h4>
            <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              <span className="font-medium text-teal-700 dark:text-teal-400">{signal.source}</span>
              <span>·</span>
              <span>{signal.signal_date}</span>
            </div>
          </div>
        </div>
        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border uppercase tracking-wider font-mono shrink-0 ${impact.bg} ${impact.text} ${impact.border}`}>
          {signal.impact_level}
        </span>
      </div>

      <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed mt-2.5">{signal.summary}</p>

      {signal.affected_skills && signal.affected_skills.length > 0 && (
        <div className="mt-3.5 pt-2.5 border-t border-slate-100 dark:border-slate-800">
          <p className="text-[10px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">Affected Skills</p>
          <div className="flex flex-wrap gap-1.5">
            {signal.affected_skills.map((s, idx) => (
              <span
                key={idx}
                className="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs font-medium border border-slate-200 dark:border-slate-700 transition-colors"
              >
                {typeof s === 'string' ? s : s.skill_name || s.skill_id}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
