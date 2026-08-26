import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/Layout';
import StatCard from '../components/StatCard';
import PassportRadar from '../components/PassportRadar';
import SignalCard from '../components/SignalCard';
import { api } from '../services/api';

const DEFAULT_STUDENTS = [
  { user_id: 'stu-001', name: 'Aarav Patil', target_role: 'AI Engineer' },
  { user_id: 'stu-002', name: 'Priya Deshmukh', target_role: 'EV Powertrain Technician' },
  { user_id: 'stu-003', name: 'Rohan Shinde', target_role: 'Cloud DevOps Specialist' },
];

const DEFAULT_PASSPORT = {
  user_id: 'stu-001',
  name: 'Aarav Patil',
  target_role: 'AI Engineer',
  skill_match_pct: 65,
  current_skills: [
    { skill_id: 'sk-001', skill_name: 'Python', proficiency: 'advanced' },
    { skill_id: 'sk-003', skill_name: 'Machine Learning', proficiency: 'intermediate' },
    { skill_id: 'sk-004', skill_name: 'SQL & Database Design', proficiency: 'intermediate' },
    { skill_id: 'sk-012', skill_name: 'Git & Version Control', proficiency: 'advanced' },
  ],
  required_skills: [
    { skill_id: 'sk-001', skill_name: 'Python', required_proficiency: 'advanced' },
    { skill_id: 'sk-002', skill_name: 'Generative AI & LLMs', required_proficiency: 'advanced' },
    { skill_id: 'sk-003', skill_name: 'Machine Learning', required_proficiency: 'advanced' },
    { skill_id: 'sk-004', skill_name: 'SQL & Database Design', required_proficiency: 'intermediate' },
    { skill_id: 'sk-008', skill_name: 'Vector DBs & RAG', required_proficiency: 'intermediate' },
    { skill_id: 'sk-010', skill_name: 'Cloud MLOps', required_proficiency: 'intermediate' },
  ],
  missing_skills: [
    { skill_id: 'sk-002', skill_name: 'Generative AI & LLMs', priority: 'CRITICAL' },
    { skill_id: 'sk-008', skill_name: 'Vector DBs & RAG', priority: 'HIGH' },
    { skill_id: 'sk-010', skill_name: 'Cloud MLOps', priority: 'MEDIUM' },
  ]
};

const DEFAULT_ROADMAP = {
  target_role: 'AI Engineer',
  roadmap: [
    {
      step: 1,
      skill_id: 'sk-002',
      skill_name: 'Generative AI & LLMs',
      category: 'Artificial Intelligence',
      trend: 'rising',
      why: 'Demanded in 68% of new tech openings in Pune and Mumbai. Critical prerequisite for next-gen application development.'
    },
    {
      step: 2,
      skill_id: 'sk-008',
      skill_name: 'Vector DBs & Retrieval-Augmented Generation (RAG)',
      category: 'Data Architecture',
      trend: 'rising',
      why: 'Highest salary premium (+28%) in enterprise software hiring across Maharashtra tech hubs.'
    },
    {
      step: 3,
      skill_id: 'sk-010',
      skill_name: 'Cloud MLOps & Model Deployment',
      category: 'Cloud Computing',
      trend: 'stable',
      why: 'Required by employers to operationalize and monitor AI workflows in production environments.'
    }
  ]
};

export default function StudentDashboard() {
  const [students, setStudents] = useState(DEFAULT_STUDENTS);
  const [selectedStudentId, setSelectedStudentId] = useState('stu-001');
  const [passport, setPassport] = useState(DEFAULT_PASSPORT);
  const [roadmap, setRoadmap] = useState(DEFAULT_ROADMAP);
  const [signals, setSignals] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.getStudents()
      .then((res) => {
        if (Array.isArray(res) && res.length > 0) {
          setStudents(res);
        }
      })
      .catch(() => {});

    api.getSignals()
      .then((res) => {
        if (Array.isArray(res)) {
          setSignals(res.slice(0, 2));
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedStudentId) return;
    setLoading(true);
    Promise.allSettled([
      api.getStudentPassport(selectedStudentId),
      api.getStudentRoadmap(selectedStudentId),
    ]).then(([pRes, rRes]) => {
      if (pRes.status === 'fulfilled' && pRes.value) {
        setPassport(pRes.value);
      }
      if (rRes.status === 'fulfilled' && rRes.value) {
        setRoadmap(rRes.value);
      }
      setLoading(false);
    });
  }, [selectedStudentId]);

  return (
    <Layout>
      {/* Header & Student Switcher */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              Student Dynamic Skill Passport
            </h1>
            <span className="text-[11px] font-mono px-2 py-0.5 bg-teal-50 dark:bg-teal-950 text-teal-800 dark:text-teal-300 font-semibold rounded border border-teal-200 dark:border-teal-800">
              NSQF Aligned
            </span>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Personalized competency tracking, target role alignment, and evidence-based learning pathway
          </p>
        </div>

        {/* Demo Student Selector */}
        <div className="flex items-center gap-2 bg-white dark:bg-slate-900 p-1.5 px-3 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs self-start md:self-auto">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">Candidate Profile:</span>
          <select
            value={selectedStudentId}
            onChange={(e) => setSelectedStudentId(e.target.value)}
            className="px-2.5 py-1 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg text-xs font-bold text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-teal-500"
          >
            {students.map((s) => (
              <option key={s.user_id} value={s.user_id}>
                {s.name} ({s.target_role})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Student Pathway Overview Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 dark:from-slate-900 dark:via-teal-950/40 dark:to-slate-900 border border-slate-800 rounded-xl p-4 sm:p-5 mb-6 text-white flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs text-teal-400 font-semibold uppercase tracking-wider">
            <span>Dynamic Alignment Workflow</span>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs sm:text-sm font-medium">
            <span className="bg-slate-800 px-2.5 py-1 rounded text-slate-200">Current Skills</span>
            <span className="text-teal-400">→</span>
            <span className="bg-rose-950/80 border border-rose-800 px-2.5 py-1 rounded text-rose-300">Target Role Gaps</span>
            <span className="text-teal-400">→</span>
            <span className="bg-teal-950/80 border border-teal-800 px-2.5 py-1 rounded text-teal-300">Recommended Roadmap</span>
            <span className="text-teal-400">→</span>
            <span className="bg-emerald-950/80 border border-emerald-800 px-2.5 py-1 rounded text-emerald-300">Industry Placement</span>
          </div>
        </div>

        <Link
          to="/student/copilot"
          className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold rounded-lg shadow-sm transition-colors shrink-0"
        >
          Consult Career Copilot →
        </Link>
      </div>

      {/* Student KPI Summary */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          title="Candidate Profile"
          value={passport?.name || 'Aarav Patil'}
          subtitle={`Profile ID: ${selectedStudentId}`}
          icon="🎓"
        />
        <StatCard
          title="Target Role"
          value={passport?.target_role || 'AI Engineer'}
          subtitle="High industry demand"
          icon="🎯"
          color="teal"
        />
        <StatCard
          title="Competency Match"
          value={`${passport?.skill_match_pct || 65}%`}
          subtitle="Match against job requirements"
          icon="📊"
          color="amber"
        />
        <StatCard
          title="Critical Gaps"
          value={`${passport?.missing_skills?.length || 3} Skills`}
          subtitle="Missing for target eligibility"
          icon="⚡"
          color="rose"
        />
      </div>

      {/* Grid: Skill Passport Radar & Competencies */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Left: Skill Passport Radar Chart */}
        <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100 dark:border-slate-800">
              <div>
                <h3 className="font-bold text-slate-900 dark:text-white text-base">Competency Benchmark Radar</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">Current proficiency evaluated against industry benchmark</p>
              </div>
              <span className="text-[11px] font-mono px-2 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold rounded border border-slate-200 dark:border-slate-700">
                NCO-2015
              </span>
            </div>

            <PassportRadar
              currentSkills={passport?.current_skills || []}
              requiredSkills={passport?.required_skills || []}
            />
          </div>

          <div className="flex justify-center items-center gap-6 mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 text-xs font-medium">
            <span className="flex items-center gap-1.5 text-teal-700 dark:text-teal-400">
              <span className="w-3 h-3 rounded-full bg-teal-600 dark:bg-teal-400"></span> Candidate Proficiency
            </span>
            <span className="flex items-center gap-1.5 text-slate-400 dark:text-slate-500">
              <span className="w-3 h-3 rounded-full bg-slate-300 dark:bg-slate-700"></span> Employer Target (100%)
            </span>
          </div>
        </div>

        {/* Right: Current vs Missing Skills List */}
        <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100 dark:border-slate-800">
              <div>
                <h3 className="font-bold text-slate-900 dark:text-white text-base">Competency Comparison Matrix</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">Acquired competencies versus employer requirement gap</p>
              </div>
              <span className="text-xs font-bold px-2 py-0.5 bg-slate-100 dark:bg-slate-800 rounded text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 font-mono">
                {passport?.current_skills?.length || 0} / {passport?.required_skills?.length || 0} Met
              </span>
            </div>

            {/* Acquired Skills */}
            <div className="mb-5">
              <p className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
                <span className="text-emerald-600 dark:text-emerald-400">✓</span> Acquired & Verified Competencies
              </p>
              <div className="flex flex-wrap gap-2">
                {passport?.current_skills?.map((sk, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 dark:bg-emerald-950/50 text-emerald-900 dark:text-emerald-300 text-xs font-semibold rounded-lg border border-emerald-200 dark:border-emerald-800"
                  >
                    <span>✓</span>
                    <span>{sk.skill_name}</span>
                    <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 bg-white dark:bg-slate-900 rounded border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300">
                      {sk.proficiency}
                    </span>
                  </span>
                ))}
              </div>
            </div>

            {/* Missing Skills */}
            <div>
              <p className="text-xs font-bold text-rose-700 dark:text-rose-400 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
                <span>⚠️</span> Target Role Competency Gaps
              </p>
              <div className="flex flex-wrap gap-2">
                {passport?.missing_skills?.map((sk, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-rose-50 dark:bg-rose-950/50 text-rose-800 dark:text-rose-300 text-xs font-semibold rounded-lg border border-rose-200 dark:border-rose-800"
                  >
                    <span>+</span>
                    <span>{sk.skill_name}</span>
                    <span className="text-[10px] bg-rose-100 dark:bg-rose-900/60 px-1.5 py-0.5 rounded font-mono font-bold text-rose-900 dark:text-rose-200">
                      {sk.priority || 'Missing'}
                    </span>
                  </span>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-6 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
            <span className="text-xs text-slate-500 dark:text-slate-400">Need personal curriculum guidance?</span>
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
      <div className="bg-white dark:bg-slate-900 p-6 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs mb-8">
        <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100 dark:border-slate-800">
          <div>
            <h3 className="font-bold text-slate-900 dark:text-white text-lg">
              Evidence-Based Learning Roadmap
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Optimal step-by-step sequence of skills to master for <strong>{passport?.target_role}</strong> based on labour-market demand
            </p>
          </div>
          <span className="text-xs font-bold px-3 py-1 bg-teal-50 dark:bg-teal-950 text-teal-800 dark:text-teal-300 rounded-full border border-teal-200 dark:border-teal-800">
            Validated Pathway
          </span>
        </div>

        <div className="space-y-4">
          {roadmap?.roadmap?.map((step, idx) => (
            <div
              key={idx}
              className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 hover:border-teal-300 dark:hover:border-teal-600 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4"
            >
              <div className="flex items-start gap-3.5">
                <span className="w-8 h-8 rounded-lg bg-slate-900 dark:bg-teal-600 text-white font-bold text-sm flex items-center justify-center shrink-0">
                  {idx + 1}
                </span>
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h4 className="font-bold text-slate-900 dark:text-white text-sm">{step.skill_name}</h4>
                    {step.category && (
                      <span className="px-2 py-0.5 rounded text-[10px] bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 font-medium">
                        {step.category}
                      </span>
                    )}
                    <span className="px-2 py-0.5 rounded text-[10px] bg-teal-100 dark:bg-teal-950 text-teal-800 dark:text-teal-300 font-semibold uppercase border border-teal-200 dark:border-teal-800 font-mono">
                      Trend: {step.trend}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 dark:text-slate-300 mt-1.5 leading-relaxed">
                    <strong className="text-teal-800 dark:text-teal-300">Why learn this?</strong> {step.why}
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
      {signals && signals.length > 0 && (
        <div className="space-y-3 mb-8">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-slate-900 dark:text-white text-base">
              Industry Demand Alerts for {passport?.target_role}
            </h3>
            <span className="text-xs text-slate-500 dark:text-slate-400">Contextual Maharashtra market intelligence</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {signals.map((sig) => (
              <SignalCard key={sig.id} signal={sig} />
            ))}
          </div>
        </div>
      )}
    </Layout>
  );
}
