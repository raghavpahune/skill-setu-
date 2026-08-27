import React from 'react';
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { useTheme } from '../context/ThemeContext';

export default function PassportRadar({ currentSkills = [], requiredSkills = [] }) {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  // Map proficiency levels to percentage scores
  const profScore = { beginner: 35, intermediate: 70, advanced: 100 };

  const data = requiredSkills.map((req) => {
    const cur = currentSkills.find((c) => c.skill_id === req.skill_id);
    const score = cur ? profScore[cur.proficiency] || 50 : 0;
    return {
      skill: req.skill_name || req.skill_id,
      CurrentProficiency: score,
      TargetRequirement: 100,
      proficiencyLabel: cur ? cur.proficiency : 'Not Acquired',
    };
  });

  if (data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-72 py-8 text-center text-xs text-slate-400 dark:text-slate-500 border border-dashed border-slate-200 dark:border-slate-800 rounded-xl bg-slate-50/50 dark:bg-slate-900/30">
        <svg className="w-8 h-8 mb-2 text-slate-300 dark:text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z" />
        </svg>
        <span className="font-semibold text-slate-700 dark:text-slate-300">No Target Competencies Defined</span>
        <span className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 max-w-xs">
          Select a candidate profile or role with active industry benchmark standards.
        </span>
      </div>
    );
  }

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const p = payload[0]?.payload;
      return (
        <div className="p-2.5 rounded-lg bg-slate-900/95 dark:bg-slate-950/95 border border-slate-700 text-white shadow-lg text-xs">
          <p className="font-bold text-slate-100 mb-1">{p?.skill}</p>
          <div className="space-y-1 text-[11px]">
            <p className="text-teal-400 flex items-center justify-between gap-3">
              <span>Candidate Level:</span>
              <span className="font-semibold uppercase font-mono">{p?.proficiencyLabel} ({p?.CurrentProficiency}%)</span>
            </p>
            <p className="text-slate-400 flex items-center justify-between gap-3">
              <span>Target Standard:</span>
              <span className="font-semibold font-mono">100% Benchmark</span>
            </p>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="w-full h-72">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="72%" data={data} margin={{ top: 10, right: 20, bottom: 10, left: 20 }}>
          <PolarGrid stroke={isDark ? '#334155' : '#e2e8f0'} />
          <PolarAngleAxis
            dataKey="skill"
            tick={{ fill: isDark ? '#cbd5e1' : '#334155', fontSize: 10, fontWeight: 500 }}
          />
          <PolarRadiusAxis
            angle={30}
            domain={[0, 100]}
            tick={{ fill: isDark ? '#64748b' : '#94a3b8', fontSize: 9 }}
          />
          <Radar
            name="Target Requirement"
            dataKey="TargetRequirement"
            stroke={isDark ? '#475569' : '#94a3b8'}
            fill={isDark ? '#334155' : '#cbd5e1'}
            fillOpacity={isDark ? 0.25 : 0.15}
            strokeDasharray="3 3"
          />
          <Radar
            name="Candidate Proficiency"
            dataKey="CurrentProficiency"
            stroke="#0d9488"
            fill="#0d9488"
            fillOpacity={0.65}
          />
          <Tooltip content={<CustomTooltip />} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
