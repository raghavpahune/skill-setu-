import React from 'react';
import { useSearchParams } from 'react-router-dom';
import Layout from '../components/Layout';
import CopilotChat from '../components/CopilotChat';

export default function CopilotPage() {
  const [searchParams] = useSearchParams();
  const urlRole = searchParams.get('role');
  const validRoles = ['government', 'institute', 'student', 'employer'];
  const initialRole = validRoles.includes(urlRole) ? urlRole : 'government';
  const initialPrompt = searchParams.get('q') || '';

  return (
    <Layout>
      <div className="max-w-5xl mx-auto py-2">
        <div className="mb-6 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-50 dark:bg-teal-950 text-teal-800 dark:text-teal-300 border border-teal-200 dark:border-teal-800 text-xs font-semibold mb-2">
            Multi-Stakeholder Conversational Decision Support
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            SkillSetu Intelligence Copilot
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-xl mx-auto">
            Query labour-market intelligence, verify district skill supply gaps, assess curriculum alignment, and guide student career choices.
          </p>
        </div>

        <CopilotChat defaultRole={initialRole} initialPrompt={initialPrompt} />
      </div>
    </Layout>
  );
}
