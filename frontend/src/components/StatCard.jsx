import React from 'react';

export default function StatCard({ title, value, subtitle, icon, trend, trendLabel, color = 'navy' }) {
  const colorStyles = {
    navy: 'bg-slate-900 dark:bg-slate-900 text-white border-slate-800 dark:border-slate-700',
    teal: 'bg-teal-50 dark:bg-teal-950/40 text-teal-900 dark:text-teal-200 border-teal-200 dark:border-teal-800',
    amber: 'bg-amber-50 dark:bg-amber-950/40 text-amber-900 dark:text-amber-200 border-amber-200 dark:border-amber-800',
    rose: 'bg-rose-50 dark:bg-rose-950/40 text-rose-900 dark:text-rose-200 border-rose-200 dark:border-rose-800',
    white: 'bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 border-slate-200 dark:border-slate-800',
  };

  return (
    <div className={`p-5 rounded-2xl border transition-all duration-200 shadow-xs hover:shadow-md ${colorStyles[color] || colorStyles.white}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider opacity-70">{title}</p>
          <p className="text-3xl font-extrabold mt-1 tracking-tight">{value}</p>
        </div>
        {icon && (
          <div className="w-10 h-10 rounded-xl bg-white/20 dark:bg-white/10 flex items-center justify-center text-xl shadow-inner">
            {icon}
          </div>
        )}
      </div>

      {(subtitle || trend) && (
        <div className="mt-3 flex items-center gap-2 text-xs">
          {trend && (
            <span className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded font-semibold ${
              trend === 'up' ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400' :
              trend === 'down' ? 'bg-rose-500/20 text-rose-600 dark:text-rose-400' :
              'bg-slate-500/20 text-slate-600 dark:text-slate-400'
            }`}>
              {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'} {trendLabel}
            </span>
          )}
          {subtitle && <span className="opacity-70">{subtitle}</span>}
        </div>
      )}
    </div>
  );
}
