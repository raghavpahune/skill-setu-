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
        criticalGaps: gapsRes.status === 'fulfilled'
          ? gapsRes.value.filter((g) => g.priority === 'CRITICAL' || g.priority === 'HIGH').length
          : 6,
        districtsCount: distRes.status === 'fulfilled' ? distRes.value.length : 10,
      });
    });
  }, []);

  const roles = [
    {
      title: 'Government & Policy Makers',
      path: '/government',
      desc: 'Monitor state-wide skill demands, district capacity gaps, and plan data-backed vocational training seat allocations.',
      badge: 'State Overview',
      accent: 'border-slate-200 dark:border-slate-800 hover:border-teal-500/80 dark:hover:border-teal-500 bg-white dark:bg-slate-900',
      btn: 'bg-slate-900 hover:bg-slate-800 dark:bg-teal-600 dark:hover:bg-teal-700 text-white',
      icon: (
        <svg className="w-6 h-6 text-teal-600 dark:text-teal-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
        </svg>
      ),
    },
    {
      title: 'Training Institutes & ITIs',
      path: '/institute',
      desc: 'Audit course placement outcomes, identify obsolete curricula, and align trade syllabus with regional industry demand.',
      badge: 'Curriculum Alignment',
      accent: 'border-slate-200 dark:border-slate-800 hover:border-teal-500/80 dark:hover:border-teal-400 bg-white dark:bg-slate-900',
      btn: 'bg-teal-700 hover:bg-teal-800 text-white',
      icon: (
        <svg className="w-6 h-6 text-teal-600 dark:text-teal-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 14l9-5-9-5-9 5 9 5zm0 0l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14zm-4 6v-7.5" />
        </svg>
      ),
    },
    {
      title: 'Students & Job Seekers',
      path: '/student',
      desc: 'Access your Dynamic Skill Passport, uncover missing competencies for target roles, and follow step-by-step learning roadmaps.',
      badge: 'Skill Passport',
      accent: 'border-slate-200 dark:border-slate-800 hover:border-blue-500/80 dark:hover:border-blue-400 bg-white dark:bg-slate-900',
      btn: 'bg-blue-700 hover:bg-blue-800 text-white',
      icon: (
        <svg className="w-6 h-6 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
        </svg>
      ),
    },
    {
      title: 'Employers & Industry',
      path: '/employer',
      desc: 'Validate AI-forecasted skill trends, correct proficiency requirements, and directly calibrate Maharashtra’s workforce pipeline.',
      badge: 'Human-in-the-Loop',
      accent: 'border-slate-200 dark:border-slate-800 hover:border-purple-500/80 dark:hover:border-purple-400 bg-white dark:bg-slate-900',
      btn: 'bg-purple-700 hover:bg-purple-800 text-white',
      icon: (
        <svg className="w-6 h-6 text-purple-600 dark:text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
      ),
    },
  ];

  const capabilities = [
    {
      tag: 'Demand Intelligence',
      label: 'Automated Skill Sensing',
      detail: 'Continuously extracts and ranks in-demand technical competencies from active job listings across Maharashtra districts.',
    },
    {
      tag: 'Gap Analytics',
      label: 'Curriculum Gap Detection',
      detail: 'Compares real employer job requirements against current ITI and polytechnic syllabi to detect critical coverage voids.',
    },
    {
      tag: 'Adaptive Recommendations',
      label: 'Evidence-Backed Actions',
      detail: 'Generates structured module and course recommendations for state boards including MSBTE and DVET.',
    },
    {
      tag: 'Student Mobility',
      label: 'Dynamic Skill Passport',
      detail: 'Provides individual proficiency radar charts, missing skill roadmaps, and direct matching with active apprenticeships.',
    },
    {
      tag: 'Human Calibration',
      label: 'Employer Feedback Loop',
      detail: 'Enables major industrial employers to confirm, correct, or reject AI skill signals with ground-truth verification.',
    },
    {
      tag: 'Predictive Horizon',
      label: 'Multi-Horizon Forecasting',
      detail: 'Projects 6, 12, and 24-month skill demand trends using industrial investment signals and macroeconomic data.',
    },
  ];

  const steps = [
    {
      num: '01',
      stage: 'Sense',
      title: 'Market Demand',
      desc: 'Ingests active job vacancies, apprenticeship notices, and government open data across Maharashtra.',
    },
    {
      num: '02',
      stage: 'Analyze',
      title: 'Skill Deficits',
      desc: 'Maps employer hiring criteria against registered ITI and polytechnic curricula to pinpoint gaps.',
    },
    {
      num: '03',
      stage: 'Synthesize',
      title: 'Recommendations',
      desc: 'AI algorithms generate evidence-backed seat allocation plans and modular syllabus upgrades.',
    },
    {
      num: '04',
      stage: 'Calibrate',
      title: 'Industry Sign-Off',
      desc: 'Regional employers review and adjust proficiency baselines through human-in-the-loop validation.',
    },
    {
      num: '05',
      stage: 'Execute',
      title: 'Workforce Action',
      desc: 'Departments fund training seats, institutes modernize courses, and candidates follow actionable pathways.',
    },
  ];

  return (
    <Layout>
      {/* Hero Section */}
      <section className="text-center pt-8 pb-12 sm:pt-14 sm:pb-16 relative">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-teal-50 dark:bg-teal-950/70 border border-teal-200 dark:border-teal-800 text-teal-800 dark:text-teal-300 text-xs font-semibold mb-6 shadow-2xs">
          <span className="w-2 h-2 rounded-full bg-teal-600 dark:bg-teal-400 animate-pulse"></span>
          <span>State-Wide Intelligence System • Maharashtra Focus</span>
        </div>

        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black text-slate-900 dark:text-white tracking-tight max-w-4xl mx-auto leading-[1.1]">
          AI-Powered Labour-Market{' '}
          <span className="bg-gradient-to-r from-teal-700 via-teal-600 to-teal-500 dark:from-teal-400 dark:via-teal-300 dark:to-emerald-200 bg-clip-text text-transparent">
            Intelligence Platform
          </span>
        </h1>

        <p className="mt-5 text-base sm:text-lg text-slate-600 dark:text-slate-300 max-w-2xl mx-auto leading-relaxed font-normal">
          SkillSetu bridges the divide between industry demand and vocational education across Maharashtra.
          We detect real-time skill gaps, automate curriculum recommendations, and guide workforce planning
          for Government, Institutes, Students, and Employers.
        </p>

        {/* Hero Actions */}
        <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
          <Link
            to="/government"
            className="w-full sm:w-auto px-6 py-2.5 bg-slate-900 dark:bg-teal-600 hover:bg-slate-800 dark:hover:bg-teal-700 text-white text-sm font-semibold rounded-lg shadow-sm transition-colors flex items-center justify-center gap-2"
          >
            <span>Explore Government Dashboard</span>
            <span>→</span>
          </Link>
          <Link
            to="/student/copilot"
            className="w-full sm:w-auto px-6 py-2.5 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-900 dark:text-white text-sm font-semibold rounded-lg border border-slate-200 dark:border-slate-700 shadow-sm transition-colors flex items-center justify-center gap-2"
          >
            <span>Ask AI Copilot</span>
            <kbd className="text-[10px] font-mono bg-slate-100 dark:bg-slate-700 px-1.5 py-0.5 rounded text-slate-500 dark:text-slate-300">⌘K</kbd>
          </Link>
        </div>

        {/* Quick Capabilities Highlights */}
        <div className="mt-8 flex flex-wrap items-center justify-center gap-2 text-xs font-medium text-slate-600 dark:text-slate-400">
          <span className="px-2.5 py-1 rounded-md bg-slate-100 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700">
            District-Level Skill Heatmaps
          </span>
          <span className="text-slate-300 dark:text-slate-700">•</span>
          <span className="px-2.5 py-1 rounded-md bg-slate-100 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700">
            MSBTE & ITI Syllabus Mapping
          </span>
          <span className="text-slate-300 dark:text-slate-700">•</span>
          <span className="px-2.5 py-1 rounded-md bg-slate-100 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700">
            Human-in-the-Loop Industry Sign-off
          </span>
        </div>
      </section>

      {/* Live Metrics Grid */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-16">
        <StatCard
          title="Active Job Postings"
          value={stats.jobsCount.toString()}
          subtitle="Indexed across Maharashtra districts"
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
      </section>

      {/* How It Works Section */}
      <section className="mb-16">
        <div className="text-center mb-10">
          <span className="text-xs font-bold uppercase tracking-wider text-teal-700 dark:text-teal-400">
            Continuous Closed-Loop System
          </span>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white mt-1">
            How SkillSetu Operates
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-xl mx-auto">
            From raw employment demand signals to data-backed educational reforms and career pathways
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {steps.map((s, i) => (
            <div
              key={s.num}
              className="relative p-5 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[11px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                    {s.stage}
                  </span>
                  <span className="text-xl font-black text-slate-300 dark:text-slate-700 font-mono">
                    {s.num}
                  </span>
                </div>
                <h3 className="font-bold text-sm text-slate-900 dark:text-white mb-1.5">
                  {s.title}
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                  {s.desc}
                </p>
              </div>
              {i < steps.length - 1 && (
                <div className="hidden lg:block absolute -right-3 top-1/2 -translate-y-1/2 text-slate-300 dark:text-slate-700 text-lg z-10 font-bold">
                  →
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Platform Capabilities Section */}
      <section className="mb-16">
        <div className="text-center mb-10">
          <span className="text-xs font-bold uppercase tracking-wider text-teal-700 dark:text-teal-400">
            System Architecture
          </span>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white mt-1">
            Platform Capabilities
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-xl mx-auto">
            Comprehensive tools built specifically for Maharashtra’s vocational and technical education ecosystem
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {capabilities.map((c) => (
            <div
              key={c.label}
              className="p-5 bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs hover:border-slate-300 dark:hover:border-slate-700 transition-colors flex flex-col justify-between"
            >
              <div>
                <span className="inline-block text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-teal-50 dark:bg-teal-950/60 text-teal-700 dark:text-teal-300 mb-2 border border-teal-200/50 dark:border-teal-800/50">
                  {c.tag}
                </span>
                <h3 className="font-bold text-sm text-slate-900 dark:text-white mb-1.5">
                  {c.label}
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                  {c.detail}
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Stakeholder Decision Hubs / Roles */}
      <section className="mb-16">
        <div className="text-center mb-8">
          <span className="text-xs font-bold uppercase tracking-wider text-teal-700 dark:text-teal-400">
            Tailored Experiences
          </span>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white mt-1">
            Stakeholder Decision Hubs
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-xl mx-auto">
            Choose your portal to access specialized analytics, recommendations, and action tools
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {roles.map((r) => (
            <div
              key={r.path}
              className={`p-6 rounded-xl border shadow-xs hover:shadow-md transition-all duration-200 flex flex-col justify-between ${r.accent}`}
            >
              <div>
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200/60 dark:border-slate-700/60">
                    {r.badge}
                  </span>
                  <div className="p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-700/60">
                    {r.icon}
                  </div>
                </div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">
                  {r.title}
                </h3>
                <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                  {r.desc}
                </p>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-end">
                <Link
                  to={r.path}
                  className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors shadow-xs flex items-center gap-1.5 ${r.btn}`}
                >
                  <span>Enter Dashboard</span>
                  <span>→</span>
                </Link>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Measurable Outcomes & State Impact */}
      <section className="mb-16 bg-slate-900 dark:bg-slate-900 border border-slate-800 rounded-xl p-8 text-white relative overflow-hidden shadow-sm">
        <div className="text-center mb-8">
          <span className="text-xs font-bold uppercase tracking-wider text-teal-400">
            Measurable Outcomes
          </span>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-white mt-1">
            Data-Driven Impact for Maharashtra
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-xl mx-auto">
            Quantifiable metrics driving curriculum alignment and industrial placement efficiency
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 text-center">
          <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-800">
            <p className="text-3xl sm:text-4xl font-black text-teal-400 font-mono">34%</p>
            <p className="text-xs text-slate-300 mt-1.5 font-medium">Average Curriculum Deficit</p>
            <p className="text-[11px] text-slate-400 mt-1">Identified across surveyed ITI trades vs industry requirements</p>
          </div>
          <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-800">
            <p className="text-3xl sm:text-4xl font-black text-teal-400 font-mono">12+</p>
            <p className="text-xs text-slate-300 mt-1.5 font-medium">Curriculum Revision Directives</p>
            <p className="text-[11px] text-slate-400 mt-1">Actionable modular interventions ready for state-level review</p>
          </div>
          <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-800">
            <p className="text-3xl sm:text-4xl font-black text-teal-400 font-mono">82%</p>
            <p className="text-xs text-slate-300 mt-1.5 font-medium">Emerging Tech Demand Growth</p>
            <p className="text-[11px] text-slate-400 mt-1">24-month forecasted surge in EV battery systems and AI applications</p>
          </div>
          <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-800">
            <p className="text-3xl sm:text-4xl font-black text-teal-400 font-mono">10</p>
            <p className="text-xs text-slate-300 mt-1.5 font-medium">Indexed District Workforce Zones</p>
            <p className="text-[11px] text-slate-400 mt-1">High-granularity clusters including Pune, Nagpur, Nashik, and Mumbai</p>
          </div>
        </div>

        <p className="text-[11px] text-slate-500 mt-8 text-center border-t border-slate-800 pt-4">
          Data reflected from active SkillSetu ingestion pipelines & synthetic demo benchmarks • Not official government gazette statistics
        </p>
      </section>
    </Layout>
  );
}
