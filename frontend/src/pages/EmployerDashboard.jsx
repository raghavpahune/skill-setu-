import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import StatCard from '../components/StatCard';
import { api } from '../services/api';

export default function EmployerDashboard() {
  const [validations, setValidations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeFeedback, setActiveFeedback] = useState(null);
  const [correctionNote, setCorrectionNote] = useState('');
  const [selectedProficiency, setSelectedProficiency] = useState('advanced');
  const [actionSuccess, setActionSuccess] = useState('');

  useEffect(() => {
    loadValidations();
  }, []);

  const loadValidations = () => {
    setLoading(true);
    api.getEmployerValidations().then((res) => {
      setValidations(res);
      setLoading(false);
    });
  };

  const handleAction = async (feedbackId, status, notes = null, prof = null) => {
    try {
      await api.submitEmployerFeedback(feedbackId, status, notes, prof);
      setActionSuccess(`Validation recorded as ${status.toUpperCase()}!`);
      setTimeout(() => setActionSuccess(''), 3000);
      setActiveFeedback(null);
      loadValidations();
    } catch (err) {
      alert('Error updating feedback');
    }
  };

  const confirmedCount = validations.filter((v) => v.status === 'confirmed').length;
  const pendingCount = validations.filter((v) => v.status === 'pending').length;
  const correctedCount = validations.filter((v) => v.status === 'corrected').length;

  return (
    <Layout>
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">🏢</span>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              Employer Validation & Industry Feedback Hub
            </h1>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Human-in-the-Loop validation: Confirm, correct, or reject AI-extracted skill demands to continuously fine-tune curriculum models
          </p>
        </div>

        {actionSuccess && (
          <div className="px-4 py-2 rounded-xl bg-emerald-50 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800 text-xs font-bold shadow-xs animate-fadeIn">
            ✓ {actionSuccess}
          </div>
        )}
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          title="Total Signals Reviewed"
          value={validations.length.toString()}
          subtitle="Employer touchpoints"
          icon="📋"
        />
        <StatCard
          title="Confirmed by Industry"
          value={confirmedCount.toString()}
          subtitle="Validated skill requirements"
          icon="✅"
          color="teal"
        />
        <StatCard
          title="Pending Verification"
          value={pendingCount.toString()}
          subtitle="Awaiting employer sign-off"
          icon="⏳"
          color="amber"
        />
        <StatCard
          title="Industry Corrections"
          value={correctedCount.toString()}
          subtitle="Human-refined parameters"
          icon="✍️"
          color="rose"
        />
      </div>

      {/* Validation Queue Table */}
      <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xs mb-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4 pb-3 border-b border-slate-100 dark:border-slate-800">
          <div>
            <h3 className="font-bold text-slate-900 dark:text-white text-base flex items-center gap-2">
              <span>🔍</span> AI Skill-Demand Summaries for Employer Validation
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Review AI extractions for your organization and provide authoritative feedback
            </p>
          </div>
          <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold self-start sm:self-auto border border-slate-200 dark:border-slate-700">
            {pendingCount} Pending Reviews
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 dark:text-slate-400 font-semibold border-b border-slate-200 dark:border-slate-700">
              <tr>
                <th className="p-3">Skill & Category</th>
                <th className="p-3">Employer</th>
                <th className="p-3">AI Estimated Demand</th>
                <th className="p-3">Required Proficiency</th>
                <th className="p-3">Validation Status</th>
                <th className="p-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {validations.map((v) => (
                <tr key={v.id} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors">
                  <td className="p-3 font-bold text-slate-900 dark:text-white">
                    <div>{v.skill_name}</div>
                    {v.notes && (
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 font-normal italic mt-0.5">
                        Note: "{v.notes}"
                      </p>
                    )}
                  </td>
                  <td className="p-3 text-slate-700 dark:text-slate-300 font-medium">{v.employer_name}</td>
                  <td className="p-3 font-semibold uppercase">
                    <span className={`px-2 py-0.5 rounded text-[11px] ${
                      v.demand_level === 'critical' ? 'bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-300 font-bold border border-rose-300 dark:border-rose-800' :
                      v.demand_level === 'high' ? 'bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-800' :
                      'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700'
                    }`}>
                      {v.demand_level}
                    </span>
                  </td>
                  <td className="p-3 font-mono capitalize text-slate-800 dark:text-slate-300">{v.proficiency_required || 'intermediate'}</td>
                  <td className="p-3">
                    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full font-bold text-[11px] ${
                      v.status === 'confirmed' ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800' :
                      v.status === 'corrected' ? 'bg-blue-100 dark:bg-blue-950 text-blue-800 dark:text-blue-300 border border-blue-300 dark:border-blue-800' :
                      v.status === 'rejected' ? 'bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-300 border border-rose-300 dark:border-rose-800' :
                      'bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-800'
                    }`}>
                      {v.status === 'confirmed' ? '✓ Confirmed' :
                       v.status === 'corrected' ? '✍️ Corrected' :
                       v.status === 'rejected' ? '✕ Rejected' : '⏳ Pending'}
                    </span>
                  </td>
                  <td className="p-3 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        onClick={() => handleAction(v.id, 'confirmed')}
                        title="Confirm AI Analysis"
                        className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-lg text-xs transition-colors shadow-2xs"
                      >
                        Confirm
                      </button>
                      <button
                        onClick={() => {
                          setActiveFeedback(v);
                          setCorrectionNote(v.notes || '');
                          setSelectedProficiency(v.proficiency_required || 'advanced');
                        }}
                        title="Provide Correction"
                        className="px-2.5 py-1 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg text-xs transition-colors shadow-2xs"
                      >
                        Correct
                      </button>
                      <button
                        onClick={() => handleAction(v.id, 'rejected')}
                        title="Reject Recommendation"
                        className="px-2.5 py-1 bg-slate-200 dark:bg-slate-800 hover:bg-rose-100 dark:hover:bg-rose-950 hover:text-rose-800 dark:hover:text-rose-300 text-slate-700 dark:text-slate-300 font-bold rounded-lg text-xs transition-colors"
                      >
                        Reject
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Correction Modal / Drawer */}
      {activeFeedback && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200 dark:border-slate-800">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800 mb-4">
              <h3 className="font-bold text-slate-900 dark:text-white text-base">
                ✍️ Submit Correction for "{activeFeedback.skill_name}"
              </h3>
              <button
                onClick={() => setActiveFeedback(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                  Required Proficiency Level for Hiring:
                </label>
                <select
                  value={selectedProficiency}
                  onChange={(e) => setSelectedProficiency(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white rounded-xl font-medium focus:ring-2 focus:ring-teal-500"
                >
                  <option value="beginner">Beginner (Foundational)</option>
                  <option value="intermediate">Intermediate (Working Knowledge)</option>
                  <option value="advanced">Advanced (Production-Grade / Senior)</option>
                </select>
              </div>

              <div>
                <label className="font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                  Employer Note / Context:
                </label>
                <textarea
                  value={correctionNote}
                  onChange={(e) => setCorrectionNote(e.target.value)}
                  placeholder="e.g. Candidates need hands-on RAG implementation rather than theoretical knowledge..."
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white rounded-xl h-24 font-normal focus:ring-2 focus:ring-teal-500"
                />
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-end gap-2">
              <button
                onClick={() => setActiveFeedback(null)}
                className="px-4 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 font-bold rounded-xl text-xs"
              >
                Cancel
              </button>
              <button
                onClick={() =>
                  handleAction(
                    activeFeedback.id,
                    'corrected',
                    correctionNote,
                    selectedProficiency
                  )
                }
                className="px-5 py-2 bg-slate-900 dark:bg-teal-600 hover:bg-slate-800 dark:hover:bg-teal-700 text-white font-bold rounded-xl text-xs shadow-xs"
              >
                Save Correction
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
