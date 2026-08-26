import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import Layout from '../components/Layout';
import StatCard from '../components/StatCard';
import MaharashtraMap from '../components/MaharashtraMap';
import SkillGapBar from '../components/SkillGapBar';
import SignalCard from '../components/SignalCard';
import RecommendationCard from '../components/RecommendationCard';
import { api } from '../services/api';
import { useTheme } from '../context/ThemeContext';

export default function GovernmentDashboard() {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const [selectedDistrict, setSelectedDistrict] = useState('Pune');
  const [gaps, setGaps] = useState([]);
  const [signals, setSignals] = useState([]);
  const [forecasts, setForecasts] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [demandStats, setDemandStats] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.allSettled([
      api.getGaps(),
      api.getSignals(),
      api.getForecasts(),
      api.getCourseRecommendations(),
      api.getJobDemand('skill'),
    ]).then(([gapsRes, sigRes, fcRes, recRes, demRes]) => {
      if (gapsRes.status === 'fulfilled') setGaps(gapsRes.value);
      if (sigRes.status === 'fulfilled') setSignals(sigRes.value.slice(0, 4));
      if (fcRes.status === 'fulfilled') setForecasts(fcRes.value.slice(0, 6));
      if (recRes.status === 'fulfilled') setRecommendations(recRes.value.slice(0, 4));
      if (demRes.status === 'fulfilled') setDemandStats(demRes.value.slice(0, 8));
      setLoading(false);
    });
  }, []);

  return (
    <Layout>
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">🏛️</span>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              Maharashtra Labour Market Intelligence Hub
            </h1>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Real-time state-level workforce demand sensing, district capacity planning, and curriculum alerts
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to={`/government/district/${encodeURIComponent(selectedDistrict)}`}
            className="px-4 py-2 bg-slate-900 dark:bg-teal-600 hover:bg-slate-800 dark:hover:bg-teal-700 text-white text-xs font-bold rounded-xl shadow-xs transition-colors flex items-center gap-1.5"
          >
            <span>Inspect {selectedDistrict} District Plan</span>
            <span>→</span>
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          title="State Job Demand"
          value="550+"
          subtitle="Indexed across 10 hubs"
          icon="💼"
        />
        <StatCard
          title="Avg Skill Deficit"
          value="34%"
          subtitle="Demand vs. ITI coverage"
          icon="⚡"
          color="amber"
        />
        <StatCard
          title="Top Emerging Field"
          value="AI & EV"
          subtitle="↑ 82% future surge"
          icon="🚀"
          color="teal"
        />
        <StatCard
          title="Curriculum Upgrades"
          value="12 Actions"
          subtitle="High priority revisions"
          icon="📘"
          color="rose"
        />
      </div>

      {/* District Map Explorer */}
      <div className="mb-8">
        <MaharashtraMap
          selectedDistrict={selectedDistrict}
          onSelectDistrict={(name) => setSelectedDistrict(name)}
        />
      </div>

      {/* Grid: Skill Demand Bar Chart & Skill Gaps */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Left: Top In-Demand Skills Chart */}
        <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xs">
          <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100 dark:border-slate-800">
            <div>
              <h3 className="font-bold text-slate-900 dark:text-white text-base flex items-center gap-2">
                <span>📊</span> Top In-Demand Skills in Maharashtra
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">Frequency of skills extracted from current job descriptions</p>
            </div>
            <span className="text-[11px] font-mono font-semibold px-2 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded border border-slate-200 dark:border-slate-700">
              Live NCO-2015
            </span>
          </div>

          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={demandStats}
                layout="vertical"
                margin={{ top: 5, right: 20, left: 40, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke={isDark ? '#1e293b' : '#f1f5f9'} />
                <XAxis type="number" tick={{ fontSize: 11, fill: isDark ? '#94a3b8' : '#64748b' }} />
                <YAxis dataKey="name" type="category" tick={{ fontSize: 11, fill: isDark ? '#cbd5e1' : '#1e293b' }} width={100} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: isDark ? '#020617' : '#0f172a',
                    borderColor: isDark ? '#1e293b' : '#334155',
                    borderRadius: '8px',
                    color: '#fff',
                    fontSize: '12px',
                  }}
                />
                <Bar dataKey="count" fill={isDark ? '#14b8a6' : '#0f172a'} radius={[0, 4, 4, 0]} name="Job Count" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Right: Critical Skill Gaps */}
        <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100 dark:border-slate-800">
              <div>
                <h3 className="font-bold text-slate-900 dark:text-white text-base flex items-center gap-2">
                  <span>⚠️</span> Priority Skill Gaps
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">Skills with high employer demand but low curriculum coverage</p>
              </div>
              <span className="text-[11px] font-bold px-2 py-0.5 bg-rose-50 dark:bg-rose-950 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800 rounded-full">
                Action Required
              </span>
            </div>

            <div className="space-y-3">
              {gaps.slice(0, 3).map((g) => (
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

          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 text-right">
            <Link
              to="/institute"
              className="text-xs font-bold text-teal-700 dark:text-teal-400 hover:text-teal-900 dark:hover:text-teal-200 hover:underline"
            >
              See Institute Curriculum Audit →
            </Link>
          </div>
        </div>
      </div>

      {/* Grid: Future Skill Forecasts & Industry Signals */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Future Forecasts */}
        <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xs">
          <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100 dark:border-slate-800">
            <div>
              <h3 className="font-bold text-slate-900 dark:text-white text-base flex items-center gap-2">
                <span>🔮</span> Future Skill Demand Forecast
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">6, 12, and 24-month horizon projection based on trends & employer surveys</p>
            </div>
            <span className="text-[11px] font-mono px-2 py-0.5 bg-teal-50 dark:bg-teal-950 text-teal-800 dark:text-teal-300 font-semibold rounded border border-teal-200 dark:border-teal-800">
              Predictive Model
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 dark:text-slate-400 font-semibold border-b border-slate-200 dark:border-slate-700">
                <tr>
                  <th className="p-2.5">Skill</th>
                  <th className="p-2.5">Horizon</th>
                  <th className="p-2.5">Future Demand</th>
                  <th className="p-2.5">Trend</th>
                  <th className="p-2.5 text-right">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {forecasts.map((f) => (
                  <tr key={f.id} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors">
                    <td className="p-2.5 font-bold text-slate-900 dark:text-white">{f.skill_name}</td>
                    <td className="p-2.5 font-mono text-slate-500 dark:text-slate-400 uppercase">{f.period}</td>
                    <td className="p-2.5">
                      <span className="px-2 py-0.5 rounded font-semibold capitalize bg-teal-50 dark:bg-teal-950 text-teal-800 dark:text-teal-300 border border-teal-200 dark:border-teal-800">
                        {f.future_demand?.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="p-2.5">
                      <span className={`font-semibold ${
                        f.trend === 'rising' ? 'text-emerald-600 dark:text-emerald-400' :
                        f.trend === 'declining' ? 'text-rose-600 dark:text-rose-400' : 'text-slate-600 dark:text-slate-400'
                      }`}>
                        {f.trend === 'rising' ? '↑ Rising' : f.trend === 'declining' ? '↓ Declining' : '→ Stable'}
                      </span>
                    </td>
                    <td className="p-2.5 text-right font-mono font-bold text-slate-700 dark:text-slate-300">
                      {f.confidence}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Industry Signals */}
        <div className="space-y-4">
          <div className="flex items-center justify-between pb-1">
            <div>
              <h3 className="font-bold text-slate-900 dark:text-white text-base flex items-center gap-2">
                <span>📡</span> Live Industry & Tech Signals
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">Government policies, technological shifts & major enterprise announcements</p>
            </div>
            <span className="text-[11px] font-bold px-2 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-full border border-slate-200 dark:border-slate-700">
              Automated Feed
            </span>
          </div>

          <div className="space-y-3">
            {signals.slice(0, 2).map((sig) => (
              <SignalCard key={sig.id} signal={sig} />
            ))}
          </div>
        </div>
      </div>

      {/* Curriculum Recommendations Section */}
      <div className="bg-slate-50 dark:bg-slate-900/60 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 mb-8">
        <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-200 dark:border-slate-800">
          <div>
            <h3 className="font-bold text-slate-900 dark:text-white text-base flex items-center gap-2">
              <span>💡</span> Actionable Curriculum Recommendations for Maharashtra
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">AI-generated evidence-backed recommendations for MSBTE & Directorate of Vocational Education</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {recommendations.map((rec, idx) => (
            <RecommendationCard key={idx} rec={rec} />
          ))}
        </div>
      </div>
    </Layout>
  );
}
