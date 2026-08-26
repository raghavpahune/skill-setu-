import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/Layout';
import StatCard from '../components/StatCard';
import { api } from '../services/api';

export default function Landing() {
  const [stats, setStats] = useState({
    jobsCount: 550,
    skillsCount: 55,
    criticalGaps: 6,
    districtsCount: 10,
  });

  useEffect(() => {
    Promise.allSettled([
      api.getJobs(),
      api.getSkills(),
      api.getGaps(),
      api.getDistricts(),
    ]).then(([jobsRes, skillsRes, gapsRes, distRes]) => {
      setStats({
        jobsCount: jobsRes.status === 'fulfilled' ? jobsRes.value.length : 550,
        skillsCount: skillsRes.status === 'fulfilled' ? skillsRes.value.length : 55,
        criticalGaps: gapsRes.status === 'fulfilled' ? gapsRes.value.filter(g => g.priority === 'CRITICAL' || g.priority === 'HIGH').length : 6,
        districtsCount: distRes.status === 'fulfilled' ? distRes.value.length : 10,
      });
    });
  }, []);

  const roles = [
    {
      title: '🏛️ Government & Policy Makers',
      path: '/government',
      desc: 'Monitor state-wide skill demands, district capacity gaps, and plan data-backed workforce investment.',
      badge: 'State Overview',
      accent: 'border-slate-300 dark:border-slate-800 hover:border-slate-900 dark:hover:border-teal-500 bg-white dark:bg-slate-900',
      btn: 'bg-slate-900 dark:bg-teal-600 text-white',
    },
    {
      title: '🎓 Training Institutes & ITIs',
      path: '/institute',
      desc: 'Audit course placement outcomes, detect obsolete curricula, and align syllabus with local industry demand.',
      badge: 'Curriculum Alignment',
      accent: 'border-teal-200 dark:border-teal-900/60 hover:border-teal-600 dark:hover:border-teal-400 bg-white dark:bg-slate-900',
      btn: 'bg-teal-700 text-white',
    },
    {
      title: '👤 Students & Job Seekers',
      path: '/student',
      desc: 'Explore your Dynamic Skill Passport, see missing competencies for target roles, and follow guided roadmaps.',
      badge: 'Skill Passport',
      accent: 'border-blue-200 dark:border-blue-900/60 hover:border-blue-600 dark:hover:border-blue-400 bg-white dark:bg-slate-900',
      btn: 'bg-blue-700 text-white',
    },
    {
      title: '🏢 Employers & Industry',
      path: '/employer',
      desc: 'Validate AI-forecasted skill trends, report hiring bottlenecks, and shape regional talent supply.',
      badge: 'Human-in-the-Loop',
      accent: 'border-purple-200 dark:border-purple-900/60 hover:border-purple-600 dark:hover:border-purple-400 bg-white dark:bg-slate-900',
      btn: 'bg-purple-700 text-white',
    },
  ];

  return (
    <Layout>
      {/* Hero Section */}
      <div className="text-center py-10 sm:py-16">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-50 dark:bg-teal-950 text-teal-800 dark:text-teal-300 border border-teal-200 dark:border-teal-800 text-xs font-semibold mb-4">
          <span>🌟</span> Smart India Hackathon 2026 · Problem Statement #26134
        </div>
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black text-slate-900 dark:text-white tracking-tight max-w-4xl mx-auto leading-tight">
          Bridging the Gap Between <br className="hidden sm:inline" />
          <span className="bg-gradient-to-r from-slate-900 via-teal-800 to-teal-600 dark:from-white dark:via-teal-300 dark:to-teal-500 bg-clip-text text-transparent">
            Labour Market & Dynamic Curriculum
          </span>
        </h1>
        <p className="mt-4 text-base sm:text-lg text-slate-600 dark:text-slate-300 max-w-2xl mx-auto leading-relaxed">
          SkillSetu continuously senses industrial job requirements, detects emerging technology signals, and translates them into actionable curriculum upgrades and student learning pathways across Maharashtra.
        </p>

        {/* Demo Flow Indicator */}
        <div className="mt-8 p-4 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xs max-w-4xl mx-auto">
          <p className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">
            🔄 Continuous Evidence-Based Loop
          </p>
          <div className="flex flex-wrap items-center justify-center gap-2 text-xs font-semibold text-slate-700 dark:text-slate-300">
            <span className="px-2.5 py-1 bg-slate-100 dark:bg-slate-800 rounded-lg">📊 Market Data</span>
            <span>→</span>
            <span className="px-2.5 py-1 bg-slate-100 dark:bg-slate-800 rounded-lg">🎯 Skill Demand</span>
            <span>→</span>
            <span className="px-2.5 py-1 bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800 rounded-lg">⚠️ Skill Gap</span>
            <span>→</span>
            <span className="px-2.5 py-1 bg-amber-50 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800 rounded-lg">📡 Industry Signal</span>
            <span>→</span>
            <span className="px-2.5 py-1 bg-teal-50 dark:bg-teal-950/60 text-teal-800 dark:text-teal-300 border border-teal-200 dark:border-teal-800 rounded-lg">🔮 Future Forecast</span>
            <span>→</span>
            <span className="px-2.5 py-1 bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 rounded-lg">📘 Curriculum Update</span>
            <span>→</span>
            <span className="px-2.5 py-1 bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 rounded-lg">👤 Skill Passport</span>
            <span>→</span>
            <span className="px-2.5 py-1 bg-purple-50 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800 rounded-lg">🏢 Employer Validation</span>
          </div>
        </div>
      </div>

      {/* Live Metrics Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-12">
        <StatCard
          title="Active Job Postings"
          value={stats.jobsCount.toString()}
          subtitle="Across 10 Maharashtra districts"
          icon="💼"
          trend="up"
          trendLabel="+18% YoY"
        />
        <StatCard
          title="Skills Tracked"
          value={stats.skillsCount.toString()}
          subtitle="Mapped to NSQF & NCO-2015"
          icon="🧠"
          color="teal"
        />
        <StatCard
          title="High Priority Gaps"
          value={stats.criticalGaps.toString()}
          subtitle="Demanded skills missing in courses"
          icon="⚠️"
          color="rose"
        />
        <StatCard
          title="Districts Indexed"
          value={stats.districtsCount.toString()}
          subtitle="Maharashtra workforce zones"
          icon="📍"
          color="navy"
        />
      </div>

      {/* Role Selection Cards */}
      <div className="mb-14">
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Select Your Role to Launch Dashboard</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Explore specialized decision-support tools built for each stakeholder</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {roles.map((r) => (
            <div
              key={r.path}
              className={`p-6 rounded-2xl border shadow-xs hover:shadow-lg transition-all duration-200 flex flex-col justify-between ${r.accent}`}
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                    {r.badge}
                  </span>
                  <span className="text-xs text-slate-400 font-mono">SIH 2026</span>
                </div>
                <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">{r.title}</h3>
                <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">{r.desc}</p>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">Interactive Demo Ready</span>
                <Link
                  to={r.path}
                  className={`px-4 py-2 rounded-xl text-xs font-bold transition-transform hover:scale-105 shadow-xs ${r.btn}`}
                >
                  Enter Dashboard →
                </Link>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Layout>
  );
}
