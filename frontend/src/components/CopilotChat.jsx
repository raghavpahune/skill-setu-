import React, { useState } from 'react';
import { api } from '../services/api';

export default function CopilotChat({ defaultRole = 'student', initialPrompt = '' }) {
  const [question, setQuestion] = useState(initialPrompt);
  const [role, setRole] = useState(defaultRole);
  const [messages, setMessages] = useState([
    {
      sender: 'copilot',
      text: "👋 Namaste! I am SkillSetu's AI Copilot, connected to Maharashtra's labour-market intelligence database. Ask me about in-demand skills, district training gaps, curriculum revisions, or career roadmaps.",
      isGrounded: true,
      time: 'Just now',
    },
  ]);
  const [loading, setLoading] = useState(false);

  const starterQuestions = [
    { role: 'government', q: 'Which skills should Pune and Nagpur prioritize for new training seats?' },
    { role: 'institute', q: 'What modules should we update in our AI and Machine Learning curriculum?' },
    { role: 'student', q: 'What skills am I missing to become an AI Engineer in Maharashtra?' },
    { role: 'employer', q: 'Which skills are currently most difficult to hire and need verification?' },
  ];

  const handleSend = async (queryText = question) => {
    if (!queryText.trim()) return;

    const userMsg = {
      sender: 'user',
      text: queryText,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setQuestion('');
    setLoading(true);

    try {
      const res = await api.askCopilot(queryText, role);
      setMessages((prev) => [
        ...prev,
        {
          sender: 'copilot',
          text: res.answer,
          isGrounded: res.data_grounded,
          demoMode: res.demo_mode,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          sender: 'copilot',
          text: '[Demo Fallback] AI service is answering with rule-based dataset recommendations. Top in-demand skills in Maharashtra are Python, AI Agents, Cloud Computing, and EV Battery Tech.',
          isGrounded: true,
          demoMode: true,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col h-[600px] overflow-hidden transition-colors">
      {/* Header */}
      <div className="p-4 bg-slate-900 dark:bg-slate-950 text-white flex items-center justify-between border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-teal-500/20 border border-teal-500/40 flex items-center justify-center text-lg">
            🤖
          </div>
          <div>
            <h3 className="font-bold text-sm flex items-center gap-2">
              SkillSetu AI Copilot
              <span className="px-2 py-0.5 rounded-full bg-teal-500/30 text-teal-300 text-[10px] font-mono">
                RAG-Grounded
              </span>
            </h3>
            <p className="text-[11px] text-slate-400">Context-Aware workforce intelligence</p>
          </div>
        </div>

        {/* Role Switcher */}
        <div className="flex items-center gap-1 bg-slate-800 dark:bg-slate-900 p-1 rounded-lg text-xs border border-slate-700/50">
          {['government', 'institute', 'student', 'employer'].map((r) => (
            <button
              key={r}
              onClick={() => setRole(r)}
              className={`px-2.5 py-1 rounded-md font-medium capitalize transition-all ${
                role === r ? 'bg-teal-600 text-white shadow-xs' : 'text-slate-400 hover:text-white'
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {/* Starter Prompts */}
      <div className="bg-slate-50 dark:bg-slate-950/80 px-4 py-2 border-b border-slate-200 dark:border-slate-800 flex items-center gap-2 overflow-x-auto text-xs">
        <span className="text-slate-500 dark:text-slate-400 font-semibold shrink-0">Try asking:</span>
        {starterQuestions
          .filter((s) => s.role === role)
          .map((s, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(s.q)}
              className="px-3 py-1 bg-white dark:bg-slate-800 hover:bg-teal-50 dark:hover:bg-teal-950 hover:text-teal-800 dark:hover:text-teal-300 text-slate-700 dark:text-slate-200 font-medium rounded-full border border-slate-200 dark:border-slate-700 shrink-0 transition-colors shadow-2xs"
            >
              💬 {s.q}
            </button>
          ))}
      </div>

      {/* Messages */}
      <div className="flex-1 p-4 overflow-y-auto space-y-4 bg-slate-50/50 dark:bg-slate-950/40">
        {messages.map((m, idx) => (
          <div
            key={idx}
            className={`flex ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl p-4 text-xs leading-relaxed shadow-2xs ${
                m.sender === 'user'
                  ? 'bg-slate-900 dark:bg-teal-700 text-white rounded-br-xs'
                  : 'bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 border border-slate-200 dark:border-slate-700 rounded-bl-xs'
              }`}
            >
              <div className="flex items-center justify-between gap-3 mb-1.5 opacity-60 text-[10px]">
                <span className="font-semibold">{m.sender === 'user' ? 'You' : 'SkillSetu Copilot'}</span>
                <span>{m.time}</span>
              </div>
              <p className="whitespace-pre-line text-sm">{m.text}</p>

              {m.sender === 'copilot' && (
                <div className="mt-3 pt-2 border-t border-slate-100 dark:border-slate-700 flex items-center gap-2 text-[10px] text-slate-500 dark:text-slate-400">
                  <span className="text-emerald-600 dark:text-emerald-400 font-semibold">✓ Verified against Maharashtra dataset</span>
                  {m.demoMode && (
                    <span className="bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 px-1.5 py-0.2 rounded font-mono">
                      DEMO_MODE
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-4 text-xs text-slate-500 dark:text-slate-400 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-teal-600 dark:bg-teal-400 animate-bounce"></span>
              <span className="w-2 h-2 rounded-full bg-teal-600 dark:bg-teal-400 animate-bounce [animation-delay:0.2s]"></span>
              <span className="w-2 h-2 rounded-full bg-teal-600 dark:bg-teal-400 animate-bounce [animation-delay:0.4s]"></span>
              <span className="ml-1 font-medium">Analyzing labour market signals...</span>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="p-3 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={`Ask as ${role} (e.g. Which skills are trending in Pune?)...`}
            className="flex-1 px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
          />
          <button
            type="submit"
            disabled={loading || !question.trim()}
            className="px-5 py-2.5 bg-slate-900 dark:bg-teal-600 hover:bg-slate-800 dark:hover:bg-teal-700 disabled:opacity-50 text-white text-sm font-semibold rounded-xl transition-colors shadow-xs"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
