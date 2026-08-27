import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { api } from '../services/api';
import { useTheme } from '../context/ThemeContext';

export default function Layout({ children }) {
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();
  const [health, setHealth] = useState({ status: 'connecting', demo_mode: true });
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    api.getHealth()
      .then((res) => setHealth(res))
      .catch(() => setHealth({ status: 'offline', demo_mode: true }));
  }, []);

  // Close mobile menu on route change
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  // Global Cmd+K / Ctrl+K shortcut to open AI Copilot
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        window.location.href = '/student/copilot';
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const navLinks = [
    { path: '/government', label: 'Government', desc: 'State & District Intelligence' },
    { path: '/institute', label: 'Institutes', desc: 'Curriculum & Course Health' },
    { path: '/student', label: 'Student Passport', desc: 'Personal Skill Pathway' },
    { path: '/employer', label: 'Employer Hub', desc: 'Signal Validation' },
    { path: '/student/copilot', label: 'AI Copilot', desc: 'Evidence-Based Q&A' },
  ];

  const isActive = (path) => {
    if (path === '/student/copilot') return location.pathname === path;
    if (path === '/student') return location.pathname === '/student';
    return location.pathname === path || (path !== '/' && location.pathname.startsWith(path) && path !== '/student');
  };

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
          <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[11px] font-mono">
            {health.demo_mode ? 'DEMO DATA ACTIVE' : 'LIVE DB CONNECTED'}
          </span>
        </div>
      </div>

      {/* Main Header */}
      <header className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 sticky top-0 z-40 shadow-xs transition-colors duration-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-14">
          <div className="flex items-center gap-3">
            <Link to="/" className="flex items-center gap-2.5 group">
              <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-slate-900 to-teal-700 dark:from-teal-800 dark:to-slate-800 flex items-center justify-center text-white font-bold text-lg shadow-sm group-hover:scale-105 transition-transform">
                S
              </div>
              <div>
                <span className="font-bold text-lg tracking-tight text-slate-900 dark:text-white flex items-center gap-1.5">
                  SkillSetu
                  <span className="text-[10px] uppercase px-1.5 py-0.5 bg-teal-50 dark:bg-teal-950/60 text-teal-700 dark:text-teal-400 font-semibold rounded border border-teal-200 dark:border-teal-800">
                    Maha-Intel
                  </span>
                </span>
                <p className="text-[10px] text-slate-500 dark:text-slate-400 leading-tight hidden sm:block">Labour-Market Intelligence & Curriculum Alignment</p>
              </div>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden lg:flex items-center gap-0.5">
            {navLinks.map((link) => (
              <Link
                key={link.path}
                to={link.path}
                className={`px-3 py-1.5 rounded-lg text-[13px] font-medium transition-colors ${
                  isActive(link.path)
                    ? 'bg-slate-900 dark:bg-teal-700 text-white'
                    : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                {link.label}
              </Link>
            ))}
          </nav>

          {/* Right actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={toggleTheme}
              aria-label="Toggle Light and Dark Theme"
              className="p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors text-xs"
              title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} Mode`}
            >
              {theme === 'light' ? '🌙' : '☀️'}
            </button>

            <Link
              to="/student/copilot"
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors"
            >
              <span>Ask Copilot</span>
              <kbd className="bg-teal-800/80 text-teal-200 text-[10px] px-1.5 py-0.5 rounded font-mono">⌘K</kbd>
            </Link>

            {/* Mobile hamburger */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="lg:hidden p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
              )}
            </button>
          </div>
        </div>

        {/* Mobile Navigation Dropdown */}
        {mobileMenuOpen && (
          <div className="lg:hidden border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 animate-fade-in shadow-md">
            <nav className="max-w-7xl mx-auto px-4 py-3 space-y-1">
              {navLinks.map((link) => (
                <Link
                  key={link.path}
                  to={link.path}
                  className={`block px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive(link.path)
                      ? 'bg-slate-900 dark:bg-teal-700 text-white'
                      : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                >
                  <span className="font-semibold">{link.label}</span>
                  <span className="text-xs text-slate-500 dark:text-slate-400 ml-2">{link.desc}</span>
                </Link>
              ))}
              <div className="pt-2 border-t border-slate-100 dark:border-slate-800 sm:hidden">
                <Link
                  to="/student/copilot"
                  className="flex items-center justify-center gap-1.5 w-full px-3 py-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold rounded-lg shadow-sm"
                >
                  <span>Ask AI Copilot</span>
                </Link>
              </div>
            </nav>
          </div>
        )}
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
          </div>
          <div className="flex items-center gap-4">
            <span className="text-slate-400 dark:text-slate-500">Continuous feedback loop: Labour Market → Gaps → Curriculum → Validation</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
