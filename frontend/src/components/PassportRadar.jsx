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

  // Map proficiency to numbers 1-3
  const profScore = { beginner: 35, intermediate: 70, advanced: 100 };

  const data = requiredSkills.map((req) => {
    const cur = currentSkills.find((c) => c.skill_id === req.skill_id);
    const score = cur ? profScore[cur.proficiency] || 50 : 0;
    return {
      skill: req.skill_name || req.skill_id,
      CurrentProficiency: score,
      TargetRequirement: 100,
    };
  });

  if (data.length === 0) {
    return <div className="text-center text-xs text-slate-400 py-8">No skill criteria found</div>;
  }

  return (
    <div className="w-full h-72">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="80%" data={data}>
          <PolarGrid stroke={isDark ? '#334155' : '#e2e8f0'} />
          <PolarAngleAxis dataKey="skill" tick={{ fill: isDark ? '#cbd5e1' : '#334155', fontSize: 11 }} />
          <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: isDark ? '#64748b' : '#94a3b8', fontSize: 10 }} />
          <Radar
            name="Target Requirement"
            dataKey="TargetRequirement"
            stroke={isDark ? '#475569' : '#94a3b8'}
            fill={isDark ? '#334155' : '#cbd5e1'}
            fillOpacity={isDark ? 0.3 : 0.2}
            strokeDasharray="3 3"
          />
          <Radar
            name="Your Current Skill"
            dataKey="CurrentProficiency"
            stroke="#14b8a6"
            fill="#14b8a6"
            fillOpacity={0.6}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: isDark ? '#020617' : '#0f172a',
              borderColor: isDark ? '#1e293b' : '#334155',
              borderRadius: '8px',
              color: '#fff',
              fontSize: '12px',
            }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
