import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { api } from '../services/api';
import { useTheme } from '../context/ThemeContext';

export default function Layout({ children }) {
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();
  const [health, setHealth] = useState({ status: 'connecting', demo_mode: true });

  useEffect(() => {
    api.getHealth()
      .then((res) => setHealth(res))
      .catch(() => setHealth({ status: 'offline', demo_mode: true }));
  }, []);

  const navLinks = [
    { path: '/government', label: '🏛️ Government', desc: 'State & District Intelligence' },
    { path: '/institute', label: '🎓 Institutes', desc: 'Curriculum & Course Health' },
    { path: '/student', label: '👤 Student Passport', desc: 'Personal Skill Pathway' },
    { path: '/employer', label: '🏢 Employer Hub', desc: 'Signal Validation' },
    { path: '/student/copilot', label: '🤖 AI Copilot', desc: 'Evidence-Based Q&A' },
  ];

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col font-sans selection:bg-teal-500 selection:text-white transition-colors duration-200">
      {/* Top Gov Banner */}
      <div className="bg-slate-900 dark:bg-slate-950 text-slate-300 dark:text-slate-400 text-xs px-4 py-1.5 border-b border-slate-800 dark:border-slate-800/80 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-teal-400">Maharashtra State Innovation Society (MSInS)</span>
          <span className="text-slate-600 hidden sm:inline">|</span>
          <span className="hidden sm:inline">Dept. of Skills, Employment, Entrepreneurship & Innovation</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-slate-800 dark:bg-slate-900 text-[11px] font-medium text-emerald-400 border border-emerald-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            SIH 2026 Live MVP
          </span>
          <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[11px] font-mono">
            {health.demo_mode ? 'DEMO DATA ACTIVE' : 'LIVE DB CONNECTED'}
          </span>
        </div>
      </div>

      {/* Main Header */}
      <header className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 sticky top-0 z-40 shadow-xs transition-colors duration-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
          <div className="flex items-center gap-3">
            <Link to="/" className="flex items-center gap-3 group">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-slate-900 to-teal-700 dark:from-teal-800 dark:to-slate-800 flex items-center justify-center text-white font-bold text-xl shadow-md group-hover:scale-105 transition-transform">
                🌉
              </div>
              <div>
                <span className="font-bold text-xl tracking-tight text-slate-900 dark:text-white flex items-center gap-1.5">
                  SkillSetu
                  <span className="text-xs uppercase px-1.5 py-0.5 bg-teal-50 dark:bg-teal-950/60 text-teal-700 dark:text-teal-400 font-semibold rounded border border-teal-200 dark:border-teal-800">
                    Maha-Intel
                  </span>
                </span>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-tight">Labour-Market Intelligence & Curriculum Alignment</p>
              </div>
            </Link>
          </div>

          {/* Navigation Tabs */}
          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => {
              const isActive = location.pathname === link.path || 
                (link.path !== '/' && location.pathname.startsWith(link.path) && link.path !== '/student' ? location.pathname.startsWith(link.path) : false);
              return (
                <Link
                  key={link.path}
                  to={link.path}
                  className={`px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-slate-900 dark:bg-teal-700 text-white shadow-sm'
                      : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>

          {/* Right quick actions: Theme Toggle + Ask Copilot */}
          <div className="flex items-center gap-2">
            {/* Theme Toggle Button */}
            <button
              onClick={toggleTheme}
              aria-label="Toggle Light and Dark Theme"
              className="p-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
              title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} Mode`}
            >
              {theme === 'light' ? (
                <span className="flex items-center gap-1.5 text-xs font-semibold">
                  🌙 <span className="hidden sm:inline">Dark</span>
                </span>
              ) : (
                <span className="flex items-center gap-1.5 text-xs font-semibold text-amber-300">
                  ☀️ <span className="hidden sm:inline">Light</span>
                </span>
              )}
            </button>

            <Link
              to="/student/copilot"
              className="inline-flex items-center gap-2 px-3 py-1.5 bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors"
            >
              <span>Ask Copilot</span>
              <span className="bg-teal-800 text-teal-200 text-[10px] px-1.5 py-0.2 rounded font-mono">⌘K</span>
            </Link>
          </div>
        </div>
      </header>

      {/* Body Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 py-6 mt-auto text-xs text-slate-500 dark:text-slate-400 transition-colors duration-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-700 dark:text-slate-300">SkillSetu Platform</span>
            <span>·</span>
            <span>Problem Statement ID: 26134</span>
            <span>·</span>
            <span>Smart India Hackathon 2026</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-slate-400 dark:text-slate-500">Continuous feedback loop: Labour Market → Gaps → Curriculum → Validation</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
