import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/Layout';
import StatCard from '../components/StatCard';
import PassportRadar from '../components/PassportRadar';
import SignalCard from '../components/SignalCard';
import { api } from '../services/api';

export default function StudentDashboard() {
  const [students, setStudents] = useState([]);
  const [selectedStudentId, setSelectedStudentId] = useState('stu-001');
  const [passport, setPassport] = useState(null);
  const [roadmap, setRoadmap] = useState(null);
  const [signals, setSignals] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getStudents().then((res) => {
      setStudents(res);
    });
    api.getSignals().then((res) => {
      setSignals(res.slice(0, 2));
    });
  }, []);

  useEffect(() => {
    if (!selectedStudentId) return;
    setLoading(true);
    Promise.allSettled([
      api.getStudentPassport(selectedStudentId),
      api.getStudentRoadmap(selectedStudentId),
    ]).then(([pRes, rRes]) => {
      if (pRes.status === 'fulfilled') setPassport(pRes.value);
      if (rRes.status === 'fulfilled') setRoadmap(rRes.value);
      setLoading(false);
    });
  }, [selectedStudentId]);

  return (
    <Layout>
      {/* Header & Student Switcher */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">👤</span>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              Dynamic Student Skill Passport
            </h1>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Personalized competency tracking, target role alignment, and evidence-based learning roadmap
          </p>
        </div>

        {/* Demo Student Selector */}
        <div className="flex items-center gap-2 bg-white dark:bg-slate-900 p-2 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 pl-2">Select Student Profile:</span>
          <select
            value={selectedStudentId}
            onChange={(e) => setSelectedStudentId(e.target.value)}
            className="px-3 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl text-xs font-bold text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-teal-500"
          >
            {students.map((s) => (
              <option key={s.user_id} value={s.user_id}>
                {s.name} ({s.target_role})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Student KPI Summary */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          title="Candidate Name"
          value={passport?.name || 'Aarav Patil'}
          subtitle={`ID: ${selectedStudentId}`}
          icon="🎓"
        />
        <StatCard
          title="Target Career"
          value={passport?.target_role || 'AI Engineer'}
          subtitle="In-demand role in Maharashtra"
          icon="🎯"
          color="teal"
        />
        <StatCard
          title="Skill Match Score"
          value={`${passport?.skill_match_pct || 52}%`}
          subtitle="Match with employer criteria"
          icon="📊"
          color="amber"
        />
        <StatCard
          title="Missing Skills"
          value={`${passport?.missing_skills?.length || 3}`}
          subtitle="Competency gaps to fill"
          icon="⚡"
          color="rose"
        />
      </div>

      {/* Grid: Skill Passport Radar & Competencies */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Left: Skill Passport Radar Chart */}
        <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xs">
          <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100 dark:border-slate-800">
            <div>
              <h3 className="font-bold text-slate-900 dark:text-white text-base flex items-center gap-2">
                <span>🕸️</span> Competency Match Radar
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">Your current proficiency vs. employer target requirements</p>
            </div>
            <span className="text-[11px] font-mono px-2 py-0.5 bg-teal-50 dark:bg-teal-950 text-teal-800 dark:text-teal-300 font-semibold rounded border border-teal-200 dark:border-teal-800">
              NSQF Aligned
            </span>
          </div>

          <PassportRadar
            currentSkills={passport?.current_skills || []}
            requiredSkills={passport?.required_skills || []}
          />

          <div className="flex justify-center items-center gap-6 mt-4 text-xs font-medium">
            <span className="flex items-center gap-1.5 text-teal-700 dark:text-teal-400">
              <span className="w-3 h-3 rounded-full bg-teal-600 dark:bg-teal-400"></span> Your Current Level
            </span>
            <span className="flex items-center gap-1.5 text-slate-400 dark:text-slate-500">
              <span className="w-3 h-3 rounded-full bg-slate-300 dark:bg-slate-700"></span> Employer Target (100%)
            </span>
          </div>
        </div>

        {/* Right: Current vs Missing Skills List */}
        <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100 dark:border-slate-800">
              <div>
                <h3 className="font-bold text-slate-900 dark:text-white text-base">Skills Breakdown</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">Acquired competencies and critical skill gaps</p>
              </div>
              <span className="text-xs font-bold px-2 py-0.5 bg-slate-100 dark:bg-slate-800 rounded text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                {passport?.current_skills?.length || 0} Acquired / {passport?.required_skills?.length || 0} Required
              </span>
            </div>

            {/* Acquired Skills */}
            <div className="mb-4">
              <p className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
                ✓ Current Acquired Skills
              </p>
              <div className="flex flex-wrap gap-2">
                {passport?.current_skills?.map((sk, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-50 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 text-xs font-semibold rounded-lg border border-emerald-200 dark:border-emerald-800"
                  >
                    <span>✓</span>
                    <span>{sk.skill_name}</span>
                    <span className="text-[10px] uppercase font-mono px-1 bg-white/70 dark:bg-slate-900 rounded">
                      {sk.proficiency}
                    </span>
                  </span>
                ))}
              </div>
            </div>

            {/* Missing Skills */}
            <div>
              <p className="text-xs font-bold text-rose-600 dark:text-rose-400 uppercase tracking-wider mb-2">
                ⚠️ Missing Skills for {passport?.target_role}
              </p>
              <div className="flex flex-wrap gap-2">
                {passport?.missing_skills?.map((sk, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1.5 px-3 py-1 bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 text-xs font-semibold rounded-lg border border-rose-200 dark:border-rose-800"
                  >
                    <span>+</span>
                    <span>{sk.skill_name}</span>
                    <span className="text-[10px] bg-rose-100 dark:bg-rose-900/60 px-1 rounded font-mono">Missing</span>
                  </span>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-6 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
            <span className="text-xs text-slate-500 dark:text-slate-400">Need personalized guidance?</span>
            <Link
              to="/student/copilot"
              className="px-3.5 py-1.5 bg-slate-900 dark:bg-teal-600 text-white text-xs font-bold rounded-lg hover:bg-slate-800 dark:hover:bg-teal-700 transition-colors shadow-2xs"
            >
              Ask Career Copilot →
            </Link>
          </div>
        </div>
      </div>

      {/* Guided Learning Roadmap with "Why Should I Learn This?" */}
      <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xs mb-8">
        <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100 dark:border-slate-800">
          <div>
            <h3 className="font-bold text-slate-900 dark:text-white text-lg flex items-center gap-2">
              <span>🗺️</span> Recommended Learning Roadmap
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Optimal sequence of competencies to master for <strong>{passport?.target_role}</strong>, with full evidence justification
            </p>
          </div>
          <span className="text-xs font-bold px-3 py-1 bg-teal-50 dark:bg-teal-950 text-teal-800 dark:text-teal-300 rounded-full border border-teal-200 dark:border-teal-800">
            Step-by-Step Pathway
          </span>
        </div>

        <div className="space-y-4">
          {roadmap?.roadmap?.map((step, idx) => (
            <div
              key={idx}
              className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 hover:border-teal-300 dark:hover:border-teal-600 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4"
            >
              <div className="flex items-start gap-3">
                <span className="w-8 h-8 rounded-xl bg-slate-900 dark:bg-teal-600 text-white font-bold text-sm flex items-center justify-center shrink-0">
                  {idx + 1}
                </span>
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="font-bold text-slate-900 dark:text-white text-sm">{step.skill_name}</h4>
                    {step.category && (
                      <span className="px-2 py-0.5 rounded text-[10px] bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 font-medium">
                        {step.category}
                      </span>
                    )}
                    <span className="px-2 py-0.5 rounded text-[10px] bg-teal-100 dark:bg-teal-950 text-teal-800 dark:text-teal-300 font-semibold uppercase border border-teal-200 dark:border-teal-800">
                      Trend: {step.trend}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 dark:text-slate-300 mt-1.5 leading-relaxed">
                    💡 <strong>Why learn this?</strong> {step.why}
                  </p>
                </div>
              </div>

              <div className="shrink-0 self-end sm:self-center">
                <Link
                  to="/student/copilot"
                  className="text-xs font-bold text-teal-700 dark:text-teal-300 hover:text-teal-900 dark:hover:text-teal-100 bg-white dark:bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 shadow-2xs hover:bg-teal-50 dark:hover:bg-slate-700 transition-colors inline-block"
                >
                  Find Courses →
                </Link>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Relevant Industry Signals */}
      <div className="space-y-3 mb-8">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-slate-900 dark:text-white text-base flex items-center gap-2">
            <span>📡</span> Industry Alerts for {passport?.target_role}
          </h3>
          <span className="text-xs text-slate-500 dark:text-slate-400">Filtered by your career interest</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {signals.map((sig) => (
            <SignalCard key={sig.id} signal={sig} />
          ))}
        </div>
      </div>
    </Layout>
  );
}
