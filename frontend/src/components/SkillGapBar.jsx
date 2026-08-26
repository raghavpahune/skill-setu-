import React from 'react';

export default function SkillGapBar({ skillName, category, demandPct, coveragePct, gapPct, priority, demandCount }) {
  const priorityColors = {
    CRITICAL: {
      bg: 'bg-rose-50 dark:bg-rose-950/50',
      text: 'text-rose-700 dark:text-rose-300',
      border: 'border-rose-300 dark:border-rose-800',
      bar: 'bg-rose-500 dark:bg-rose-400',
    },
    HIGH: {
      bg: 'bg-amber-50 dark:bg-amber-950/50',
      text: 'text-amber-700 dark:text-amber-300',
      border: 'border-amber-300 dark:border-amber-800',
      bar: 'bg-amber-500 dark:bg-amber-400',
    },
    MEDIUM: {
      bg: 'bg-blue-50 dark:bg-blue-950/50',
      text: 'text-blue-700 dark:text-blue-300',
      border: 'border-blue-300 dark:border-blue-800',
      bar: 'bg-blue-500 dark:bg-blue-400',
    },
    LOW: {
      bg: 'bg-slate-50 dark:bg-slate-800',
      text: 'text-slate-700 dark:text-slate-300',
      border: 'border-slate-300 dark:border-slate-700',
      bar: 'bg-slate-400 dark:bg-slate-500',
    },
  };

  const style = priorityColors[priority] || priorityColors.LOW;

  return (
    <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs hover:border-slate-300 dark:hover:border-slate-700 transition-all">
      <div className="flex items-start justify-between gap-2 mb-2">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-900 dark:text-white">{skillName}</span>
            {category && (
              <span className="px-2 py-0.5 rounded text-[11px] bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-medium border border-slate-200 dark:border-slate-700">
                {category}
              </span>
            )}
          </div>
          {demandCount !== undefined && (
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Found in {demandCount} active job descriptions</p>
          )}
        </div>
        <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full border uppercase tracking-wider ${style.bg} ${style.text} ${style.border}`}>
          {priority} GAP ({gapPct}%)
        </span>
      </div>

      {/* Progress Bars */}
      <div className="space-y-2 text-xs">
        <div>
          <div className="flex justify-between text-slate-600 dark:text-slate-400 mb-1">
            <span>Market Demand Score</span>
            <span className="font-semibold text-slate-900 dark:text-slate-200">{demandPct}%</span>
          </div>
          <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2 overflow-hidden">
            <div
              className="bg-slate-900 dark:bg-teal-400 h-2 rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, demandPct)}%` }}
            ></div>
          </div>
        </div>

        <div>
          <div className="flex justify-between text-slate-600 dark:text-slate-400 mb-1">
            <span>Institute Curriculum Coverage</span>
            <span className="font-semibold text-slate-900 dark:text-slate-200">{coveragePct}%</span>
          </div>
          <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2 overflow-hidden">
            <div
              className="bg-teal-600 dark:bg-emerald-500 h-2 rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, coveragePct)}%` }}
            ></div>
          </div>
        </div>
      </div>
    </div>
  );
}
