import React, { useState } from 'react';

export default function RecommendationCard({ rec }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs hover:border-teal-300 dark:hover:border-teal-700 transition-all">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-teal-100 dark:bg-teal-950 text-teal-800 dark:text-teal-300 text-xs font-bold">
              💡
            </span>
            <h4 className="font-bold text-slate-900 dark:text-white text-sm">{rec.recommendation}</h4>
          </div>
          <p className="text-xs text-slate-600 dark:text-slate-300 mt-2 leading-relaxed">{rec.reason}</p>
        </div>

        {rec.confidence && (
          <div className="text-right shrink-0">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 block">AI Confidence</span>
            <span className="inline-block px-2.5 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 font-bold text-xs border border-emerald-200 dark:border-emerald-800 mt-0.5">
              {rec.confidence}%
            </span>
          </div>
        )}
      </div>

      <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs">
          {rec.priority && (
            <span className="px-2 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded font-medium border border-slate-200 dark:border-slate-700">
              Priority: <strong className="text-slate-900 dark:text-white">{rec.priority}</strong>
            </span>
          )}
          {rec.future_demand && (
            <span className="px-2 py-0.5 bg-teal-50 dark:bg-teal-950 text-teal-800 dark:text-teal-300 rounded font-medium border border-teal-200 dark:border-teal-800">
              Future Trend: <strong>{rec.trend || 'rising'}</strong>
            </span>
          )}
        </div>

        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs font-semibold text-teal-700 dark:text-teal-400 hover:text-teal-900 dark:hover:text-teal-200 flex items-center gap-1 transition-colors"
        >
          <span>Why is this recommended?</span>
          <span>{expanded ? '▲' : '▼'}</span>
        </button>
      </div>

      {expanded && (
        <div className="mt-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-xs text-slate-700 dark:text-slate-300 space-y-1.5 animate-fadeIn">
          <p className="font-semibold text-slate-900 dark:text-white">📊 Supporting Evidence Breakdown:</p>
          <ul className="list-disc list-inside space-y-1 text-slate-600 dark:text-slate-300 pl-1">
            <li><strong>Skill Gap:</strong> {rec.gap_pct}% gap between industry demand and curriculum.</li>
            <li><strong>Future Outlook:</strong> Categorized as <em>{rec.future_demand}</em> demand over the next 12-24 months.</li>
            {rec.related_signals && rec.related_signals.length > 0 && (
              <li><strong>Market Signals:</strong> Correlated with "{rec.related_signals.join(', ')}".</li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
