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
      title: 'Government & Policy Makers',
      path: '/government',
      desc: 'Monitor state-wide skill demands, district capacity gaps, and plan data-backed workforce investment.',
      badge: 'State Overview',
      icon: '🏛️',
      accent: 'border-slate-200 dark:border-slate-800 hover:border-slate-400 dark:hover:border-teal-500 bg-white dark:bg-slate-900',
      btn: 'bg-slate-900 dark:bg-teal-600 text-white',
    },
    {
      title: 'Training Institutes & ITIs',
      path: '/institute',
      desc: 'Audit course placement outcomes, detect obsolete curricula, and align syllabus with local industry demand.',
      badge: 'Curriculum Alignment',
      icon: '🎓',
      accent: 'border-slate-200 dark:border-slate-800 hover:border-teal-500 dark:hover:border-teal-400 bg-white dark:bg-slate-900',
      btn: 'bg-teal-700 text-white',
    },
    {
      title: 'Students & Job Seekers',
      path: '/student',
      desc: 'Explore your Dynamic Skill Passport, see missing competencies for target roles, and follow guided roadmaps.',
      badge: 'Skill Passport',
      icon: '👤',
      accent: 'border-slate-200 dark:border-slate-800 hover:border-blue-500 dark:hover:border-blue-400 bg-white dark:bg-slate-900',
      btn: 'bg-blue-700 text-white',
    },
    {
      title: 'Employers & Industry',
      path: '/employer',
      desc: 'Validate AI-forecasted skill trends, report hiring bottlenecks, and shape regional talent supply.',
      badge: 'Human-in-the-Loop',
      icon: '🏢',
      accent: 'border-slate-200 dark:border-slate-800 hover:border-purple-500 dark:hover:border-purple-400 bg-white dark:bg-slate-900',
      btn: 'bg-purple-700 text-white',
    },
  ];

  const capabilities = [
    { label: 'Skill Demand Sensing', detail: 'Continuously extract and rank in-demand skills from live job postings across Maharashtra districts.' },
    { label: 'Skill Gap Detection', detail: 'Compare employer requirements against existing ITI/polytechnic curriculum to identify critical coverage gaps.' },
    { label: 'Curriculum Recommendations', detail: 'AI-generated, evidence-backed module recommendations for MSBTE and Directorate of Vocational Education.' },
    { label: 'Student Skill Passport', detail: 'Dynamic competency tracking with target-role alignment, gap analysis, and guided learning roadmaps.' },
    { label: 'Employer Validation', detail: 'Human-in-the-loop workflow where employers confirm, correct, or reject AI-extracted skill signals.' },
    { label: 'Predictive Forecasting', detail: '6, 12, and 24-month skill demand projections based on industry trends and employer surveys.' },
  ];

  const steps = [
    { num: '01', title: 'Sense Market Demand', desc: 'Ingest job postings, employer surveys, and industry signals across Maharashtra.' },
    { num: '02', title: 'Detect Skill Gaps', desc: 'Compare demand against current curriculum coverage in ITIs and polytechnics.' },
    { num: '03', title: 'Generate Recommendations', desc: 'AI produces evidence-backed curriculum, training, and career recommendations.' },
    { num: '04', title: 'Validate with Employers', desc: 'Human-in-the-loop feedback refines AI predictions with ground-truth data.' },
    { num: '05', title: 'Act on Intelligence', desc: 'Government plans training seats, institutes update curricula, students follow roadmaps.' },
  ];

  return (
    <Layout>
      {/* Hero Section */}
      <section className="text-center pt-8 pb-12 sm:pt-12 sm:pb-16">
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black text-slate-900 dark:text-white tracking-tight max-w-4xl mx-auto leading-[1.1]">
          AI-Powered Labour-Market{' '}
          <span className="bg-gradient-to-r from-teal-700 to-teal-500 dark:from-teal-400 dark:to-teal-200 bg-clip-text text-transparent">
            Intelligence Platform
          </span>
        </h1>
        <p className="mt-5 text-base sm:text-lg text-slate-600 dark:text-slate-300 max-w-2xl mx-auto leading-relaxed">
          SkillSetu converts changing industry demand into actionable skill-gap insights,
          curriculum recommendations, and career pathways — connecting Government, Institutes,
          Students, and Employers across Maharashtra.
        </p>
        <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
          <Link
            to="/government"
            className="px-6 py-2.5 bg-slate-900 dark:bg-teal-600 hover:bg-slate-800 dark:hover:bg-teal-700 text-white text-sm font-semibold rounded-lg shadow-sm transition-colors"
          >
            Explore Government Dashboard
          </Link>
          <Link
            to="/student/copilot"
            className="px-6 py-2.5 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-900 dark:text-white text-sm font-semibold rounded-lg border border-slate-200 dark:border-slate-700 shadow-sm transition-colors"
          >
            Ask AI Copilot
          </Link>
        </div>
      </section>

      {/* Live Metrics */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-16">
        <StatCard title="Active Job Postings" value={stats.jobsCount.toString()} subtitle="Across 10 Maharashtra districts" icon="💼" trend="up" trendLabel="+18% YoY" />
        <StatCard title="Skills Tracked" value={stats.skillsCount.toString()} subtitle="Mapped to NSQF & NCO-2015" icon="🧠" color="teal" />
        <StatCard title="High Priority Gaps" value={stats.criticalGaps.toString()} subtitle="Demanded skills missing in courses" icon="⚠️" color="rose" />
        <StatCard title="Districts Indexed" value={stats.districtsCount.toString()} subtitle="Maharashtra workforce zones" icon="📍" color="navy" />
      </section>

      {/* How It Works */}
      <section className="mb-16">
        <div className="text-center mb-10">
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">How SkillSetu Works</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-xl mx-auto">
            A continuous evidence-based loop from market data to workforce action
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          {steps.map((s, i) => (
            <div key={s.num} className="relative p-5 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
              <span className="text-3xl font-black text-slate-200 dark:text-slate-800 absolute top-3 right-4">{s.num}</span>
              <h3 className="font-bold text-sm text-slate-900 dark:text-white mb-1.5">{s.title}</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">{s.desc}</p>
              {i < steps.length - 1 && (
                <span className="hidden lg:block absolute -right-3 top-1/2 -translate-y-1/2 text-slate-300 dark:text-slate-700 text-lg">→</span>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Platform Capabilities */}
      <section className="mb-16">
        <div className="text-center mb-10">
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Platform Capabilities</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-xl mx-auto">
            End-to-end labour-market intelligence for data-driven workforce decisions
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {capabilities.map((c) => (
            <div key={c.label} className="p-5 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
              <h3 className="font-bold text-sm text-slate-900 dark:text-white mb-1.5">{c.label}</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">{c.detail}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Role Selection Cards */}
      <section className="mb-16">
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Select Your Role</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Specialized decision-support tools for each stakeholder
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {roles.map((r) => (
            <div
              key={r.path}
              className={`p-6 rounded-xl border shadow-xs hover:shadow-md transition-all duration-200 flex flex-col justify-between ${r.accent}`}
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                    {r.badge}
                  </span>
                  <span className="text-2xl">{r.icon}</span>
                </div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">{r.title}</h3>
                <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">{r.desc}</p>
              </div>

              <div className="mt-5 pt-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-end">
                <Link
                  to={r.path}
                  className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors shadow-xs ${r.btn}`}
                >
                  Enter Dashboard →
                </Link>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Key Outcomes */}
      <section className="mb-16 bg-slate-900 dark:bg-slate-800 rounded-xl p-8 text-white">
        <h2 className="text-xl font-bold mb-6 text-center">Key Outcomes</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 text-center">
          <div>
            <p className="text-3xl font-black text-teal-400">34%</p>
            <p className="text-xs text-slate-300 mt-1">Average skill deficit detected across Maharashtra ITIs</p>
          </div>
          <div>
            <p className="text-3xl font-black text-teal-400">12</p>
            <p className="text-xs text-slate-300 mt-1">High-priority curriculum revision actions identified</p>
          </div>
          <div>
            <p className="text-3xl font-black text-teal-400">82%</p>
            <p className="text-xs text-slate-300 mt-1">Projected surge in AI & EV skill demand (24 months)</p>
          </div>
          <div>
            <p className="text-3xl font-black text-teal-400">10</p>
            <p className="text-xs text-slate-300 mt-1">District workforce hubs indexed with scalable architecture</p>
          </div>
        </div>
        <p className="text-[10px] text-slate-500 mt-6 text-center">Based on demo synthetic data · Not official government statistics</p>
      </section>
    </Layout>
  );
}
