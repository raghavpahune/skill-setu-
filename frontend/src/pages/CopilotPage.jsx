import React from 'react';
import Layout from '../components/Layout';
import CopilotChat from '../components/CopilotChat';

export default function CopilotPage() {
  return (
    <Layout>
      <div className="max-w-4xl mx-auto py-2">
        <div className="mb-6 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-50 dark:bg-teal-950 text-teal-800 dark:text-teal-300 border border-teal-200 dark:border-teal-800 text-xs font-semibold mb-2">
            <span>🤖</span> Multi-Stakeholder Conversational Intelligence
          </div>
          <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            SkillSetu AI Career & Policy Copilot
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-xl mx-auto">
            Ask complex workforce questions grounded in live Maharashtra labour-market data, curriculum records, and employer validation signals.
          </p>
        </div>

        <CopilotChat defaultRole="government" />
      </div>
    </Layout>
  );
}
