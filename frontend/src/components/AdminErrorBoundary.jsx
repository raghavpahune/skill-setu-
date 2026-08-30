import React from 'react';
import Layout from './Layout';

export default class AdminErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('[SkillSetu Admin Error Boundary Caught]', error, errorInfo);
    this.setState({ errorInfo });
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.reload();
  };

  handleGoOverview = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.href = '/admin?tab=overview';
  };

  handleLogout = () => {
    try {
      window.localStorage.removeItem('skillsetu_auth_token');
    } catch {
      // ignore
    }
    window.location.href = '/login';
  };

  render() {
    if (this.state.hasError) {
      return (
        <Layout>
          <div className="max-w-2xl mx-auto my-12 p-6 sm:p-8 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl text-center animate-fadeIn">
            <div className="w-16 h-16 rounded-2xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800/80 flex items-center justify-center text-3xl mx-auto mb-4 shadow-xs">
              ⚠️
            </div>

            <span className="inline-block px-3 py-1 rounded-full text-xs font-mono font-bold bg-rose-100 dark:bg-rose-900/60 text-rose-800 dark:text-rose-300 border border-rose-300 dark:border-rose-700 mb-3">
              ADMIN CONSOLE EXCEPTION CAUGHT
            </span>

            <h2 className="text-2xl font-black text-slate-900 dark:text-white tracking-tight mb-2">
              Admin Dashboard Error
            </h2>

            <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 mb-6 leading-relaxed max-w-lg mx-auto">
              Something went wrong while loading the administration console. The safety boundary prevented the application from crashing.
            </p>

            {this.state.error?.message && (
              <div className="mb-6 p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-left font-mono text-[11px] text-rose-600 dark:text-rose-400 overflow-x-auto max-h-32">
                <span className="font-bold text-slate-700 dark:text-slate-300">Diagnostic: </span>
                {this.state.error.message}
              </div>
            )}

            <div className="flex flex-wrap items-center justify-center gap-3">
              <button
                type="button"
                onClick={this.handleRetry}
                className="px-4 py-2 text-xs font-bold rounded-xl bg-teal-600 hover:bg-teal-700 text-white shadow-xs transition-colors cursor-pointer"
              >
                Retry ⟳
              </button>
              <button
                type="button"
                onClick={this.handleGoOverview}
                className="px-4 py-2 text-xs font-bold rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition-colors cursor-pointer border border-slate-200 dark:border-slate-700"
              >
                Go to Admin Overview →
              </button>
              <button
                type="button"
                onClick={this.handleLogout}
                className="px-4 py-2 text-xs font-bold rounded-xl bg-rose-50 hover:bg-rose-100 dark:bg-rose-950 dark:hover:bg-rose-900 text-rose-700 dark:text-rose-300 transition-colors cursor-pointer border border-rose-200 dark:border-rose-800"
              >
                Logout 🚪
              </button>
            </div>
          </div>
        </Layout>
      );
    }

    return this.props.children;
  }
}
