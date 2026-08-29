import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { api } from '../services/api';
import { useTheme } from '../context/ThemeContext';
import { useTour } from '../context/TourContext';

export default function Layout({ children }) {
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();
  const { startTour } = useTour();
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
    { path: '/admin', label: 'Admin Data', desc: 'Assessment Data Management' },
  ];

  const isActive = (path) => {
    if (path === '/student/copilot') return location.pathname === path;
    if (path === '/student') return location.pathname === '/student';
    if (path === '/admin') return location.pathname === '/admin';
    return location.pathname === path || (path !== '/' && location.pathname.startsWith(path) && path !== '/student');
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col font-sans selection:bg-teal-500 selection:text-white transition-colors duration-200">
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
            <span className="hidden sm:inline-flex px-2 py-0.5 rounded bg-amber-500/15 dark:bg-amber-500/20 text-amber-800 dark:text-amber-300 border border-amber-500/30 text-[11px] font-mono font-medium">
              {health.demo_mode ? 'DEMO DATA ACTIVE' : 'LIVE DB CONNECTED'}
            </span>

            <button
              onClick={startTour}
              className="hidden md:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-700 hover:to-emerald-700 text-white text-xs font-bold shadow-xs transition-all cursor-pointer"
            >
              <span>✨</span>
              <span>SIH Demo Tour</span>
            </button>

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
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 dark:bg-slate-800 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg shadow-sm border border-slate-700/60 transition-colors"
            >
              <span>Ask Copilot</span>
              <kbd className="bg-slate-800 text-teal-300 text-[10px] px-1.5 py-0.5 rounded font-mono">⌘K</kbd>
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
              <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-100 dark:border-slate-800">
                <span className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">Pipeline Status</span>
                <span className="px-2 py-0.5 rounded bg-amber-500/15 dark:bg-amber-500/20 text-amber-800 dark:text-amber-300 border border-amber-500/30 text-[10px] font-mono font-semibold">
                  {health.demo_mode ? 'DEMO DATA ACTIVE' : 'LIVE DB CONNECTED'}
                </span>
              </div>
              <button
                onClick={() => { setMobileMenuOpen(false); startTour(); }}
                className="w-full text-left px-3 py-2.5 rounded-lg bg-teal-50 dark:bg-teal-950/60 text-teal-800 dark:text-teal-300 font-bold text-sm flex items-center gap-2 border border-teal-200 dark:border-teal-800 mb-2 cursor-pointer"
              >
                <span>✨</span>
                <span>Launch SIH Demo Tour</span>
              </button>
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

      {/* Professional Structured Footer */}
      <footer className="bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 py-10 mt-auto text-xs text-slate-500 dark:text-slate-400 transition-colors duration-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 mb-8">
            {/* Col 1: Platform & Identity */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded bg-gradient-to-tr from-slate-900 to-teal-700 dark:from-teal-800 dark:to-slate-800 flex items-center justify-center text-white font-bold text-sm shadow-xs">
                  S
                </div>
                <span className="font-bold text-sm text-slate-900 dark:text-white">
                  SkillSetu Maha-Intel
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                Labour-Market Intelligence & Curriculum-Alignment Platform. Connecting Maharashtra's state agencies, vocational institutes, candidates, and industry partners.
              </p>
              <div className="inline-flex items-center gap-1.5 text-[11px] font-mono text-teal-700 dark:text-teal-400 bg-teal-50 dark:bg-teal-950/60 px-2 py-0.5 rounded border border-teal-200 dark:border-teal-800">
                <span className="w-1.5 h-1.5 rounded-full bg-teal-500"></span>
                <span>Active Intelligence Pipeline</span>
              </div>
            </div>

            {/* Col 2: Stakeholder Portals */}
            <div>
              <h4 className="font-bold text-slate-900 dark:text-white text-xs uppercase tracking-wider mb-3">
                Stakeholder Portals
              </h4>
              <ul className="space-y-2 text-xs">
                <li>
                  <Link to="/government" className="hover:text-teal-600 dark:hover:text-teal-400 transition-colors">
                    State Government Overview
                  </Link>
                </li>
                <li>
                  <Link to="/institute" className="hover:text-teal-600 dark:hover:text-teal-400 transition-colors">
                    Training Institutes & ITIs
                  </Link>
                </li>
                <li>
                  <Link to="/student" className="hover:text-teal-600 dark:hover:text-teal-400 transition-colors">
                    Candidate Skill Passport
                  </Link>
                </li>
                <li>
                  <Link to="/employer" className="hover:text-teal-600 dark:hover:text-teal-400 transition-colors">
                    Employer Validation Hub
                  </Link>
                </li>
                <li>
                  <Link to="/admin" className="hover:text-teal-600 dark:hover:text-teal-400 transition-colors">
                    Admin Data Management
                  </Link>
                </li>
              </ul>
            </div>


            {/* Col 3: Intelligence & Navigation */}
            <div>
              <h4 className="font-bold text-slate-900 dark:text-white text-xs uppercase tracking-wider mb-3">
                Intelligence Tools
              </h4>
              <ul className="space-y-2 text-xs">
                <li>
                  <Link to="/student/copilot" className="hover:text-teal-600 dark:hover:text-teal-400 transition-colors flex items-center gap-1">
                    <span>Evidence-Based AI Copilot</span>
                    <span className="text-[10px] font-mono bg-slate-100 dark:bg-slate-800 px-1 rounded">⌘K</span>
                  </Link>
                </li>
                <li>
                  <Link to="/government/district/Pune" className="hover:text-teal-600 dark:hover:text-teal-400 transition-colors">
                    District Workforce Plans
                  </Link>
                </li>
                <li>
                  <span className="text-slate-400 dark:text-slate-500">NSQF & NCO-2015 Classification</span>
                </li>
                <li>
                  <span className="text-slate-400 dark:text-slate-500">Open Data Ingestion Pipeline</span>
                </li>
              </ul>
            </div>

            {/* Col 4: State Alignment */}
            <div>
              <h4 className="font-bold text-slate-900 dark:text-white text-xs uppercase tracking-wider mb-3">
                Governance & Alignment
              </h4>
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-2 leading-relaxed">
                Aligned with Dept. of Skills, Employment, Entrepreneurship & Innovation, Government of Maharashtra.
              </p>
              <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800 text-[11px] text-slate-600 dark:text-slate-400 space-y-1">
                <div className="flex justify-between">
                  <span>Data Engine:</span>
                  <span className="font-mono text-slate-800 dark:text-slate-200">FastAPI + Async</span>
                </div>
                <div className="flex justify-between">
                  <span>System Status:</span>
                  <span className="font-semibold text-emerald-600 dark:text-emerald-400">Operational</span>
                </div>
              </div>
            </div>
          </div>

          {/* Bottom Bar */}
          <div className="pt-6 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4 text-[11px] text-slate-400 dark:text-slate-500">
            <div>
              © {new Date().getFullYear()} SkillSetu. Continuous evidence-based feedback loop: Labour Market → Gaps → Curriculum → Validation.
            </div>
            <div className="flex items-center gap-4">
              <span>District Micro-Plans</span>
              <span>•</span>
              <span>Predictive Horizons</span>
              <span>•</span>
              <span>Human-in-the-Loop</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
