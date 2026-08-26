import React from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import Landing from './pages/Landing';
import GovernmentDashboard from './pages/GovernmentDashboard';
import DistrictPlan from './pages/DistrictPlan';
import InstituteDashboard from './pages/InstituteDashboard';
import StudentDashboard from './pages/StudentDashboard';
import CopilotPage from './pages/CopilotPage';
import EmployerDashboard from './pages/EmployerDashboard';
import Layout from './components/Layout';

function NotFound() {
  return (
    <Layout>
      <div className="py-20 text-center">
        <p className="text-6xl font-black text-slate-300 dark:text-slate-700">404</p>
        <h1 className="text-xl font-bold text-slate-900 dark:text-white mt-4">Page Not Found</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">The requested route does not exist in SkillSetu.</p>
        <Link to="/" className="inline-block mt-6 px-5 py-2 bg-slate-900 dark:bg-teal-600 text-white text-sm font-semibold rounded-lg hover:bg-slate-800 dark:hover:bg-teal-700 transition-colors">
          Return to Home
        </Link>
      </div>
    </Layout>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/government" element={<GovernmentDashboard />} />
          <Route path="/government/district/:name" element={<DistrictPlan />} />
          <Route path="/institute" element={<InstituteDashboard />} />
          <Route path="/student" element={<StudentDashboard />} />
          <Route path="/student/copilot" element={<CopilotPage />} />
          <Route path="/employer" element={<EmployerDashboard />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}
