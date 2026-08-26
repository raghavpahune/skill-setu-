import React from 'react';

export default function StatCard({ title, value, subtitle, icon, trend, trendLabel, color = 'white' }) {
  const colorStyles = {
    navy: 'bg-slate-900 dark:bg-slate-900 text-white border-slate-800 dark:border-slate-700',
    teal: 'bg-teal-50/70 dark:bg-teal-950/30 text-teal-950 dark:text-teal-200 border-teal-200/80 dark:border-teal-800/80',
    amber: 'bg-amber-50/70 dark:bg-amber-950/30 text-amber-950 dark:text-amber-200 border-amber-200/80 dark:border-amber-800/80',
    rose: 'bg-rose-50/70 dark:bg-rose-950/30 text-rose-950 dark:text-rose-200 border-rose-200/80 dark:border-rose-800/80',
    white: 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 border-slate-200 dark:border-slate-800',
  };

  return (
    <div className={`p-4 sm:p-5 rounded-xl border transition-all duration-200 shadow-xs hover:shadow-sm ${colorStyles[color] || colorStyles.white}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wider opacity-70">{title}</p>
          <p className="text-2xl sm:text-3xl font-extrabold mt-1 tracking-tight">{value}</p>
        </div>
        {icon && (
          <div className="w-9 h-9 rounded-lg bg-black/5 dark:bg-white/10 flex items-center justify-center text-lg shadow-2xs shrink-0">
            {icon}
          </div>
        )}
      </div>

      {(subtitle || trend) && (
        <div className="mt-2.5 flex items-center gap-2 text-xs flex-wrap">
          {trend && (
            <span className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded font-semibold ${
              trend === 'up' ? 'bg-emerald-500/20 text-emerald-700 dark:text-emerald-400' :
              trend === 'down' ? 'bg-rose-500/20 text-rose-700 dark:text-rose-400' :
              'bg-slate-500/20 text-slate-700 dark:text-slate-400'
            }`}>
              {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'} {trendLabel}
            </span>
          )}
          {subtitle && <span className="opacity-70 text-[11px] line-clamp-1">{subtitle}</span>}
        </div>
      )}
    </div>
  );
}
