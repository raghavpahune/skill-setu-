import React from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { TourProvider } from './context/TourContext';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import DemoTour from './components/DemoTour';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Register from './pages/Register';
import GovernmentDashboard from './pages/GovernmentDashboard';
import DistrictPlan from './pages/DistrictPlan';
import InstituteDashboard from './pages/InstituteDashboard';
import StudentDashboard from './pages/StudentDashboard';
import CopilotPage from './pages/CopilotPage';
import EmployerDashboard from './pages/EmployerDashboard';
import AdminDashboard from './pages/AdminDashboard';
import AdminErrorBoundary from './components/AdminErrorBoundary';
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
        <AuthProvider>
          <TourProvider>
            <DemoTour />
            <Routes>
              <Route path="/" element={<Landing />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route
                path="/government"
                element={
                  <ProtectedRoute allowedRoles={['GOVERNMENT', 'ADMIN']}>
                    <GovernmentDashboard />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/government/district/:name"
                element={
                  <ProtectedRoute allowedRoles={['GOVERNMENT', 'ADMIN']}>
                    <DistrictPlan />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/institute"
                element={
                  <ProtectedRoute allowedRoles={['INSTITUTE', 'ADMIN']}>
                    <InstituteDashboard />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/student"
                element={
                  <ProtectedRoute allowedRoles={['STUDENT', 'ADMIN']}>
                    <StudentDashboard />
                  </ProtectedRoute>
                }
              />
              <Route path="/copilot" element={<CopilotPage />} />
              <Route path="/student/copilot" element={<CopilotPage roleOverride="student" />} />
              <Route path="/employer/copilot" element={<CopilotPage roleOverride="employer" />} />
              <Route path="/institute/copilot" element={<CopilotPage roleOverride="institute" />} />
              <Route path="/government/copilot" element={<CopilotPage roleOverride="government" />} />
              <Route path="/admin/copilot" element={<CopilotPage roleOverride="admin" />} />
              <Route
                path="/employer"
                element={
                  <ProtectedRoute allowedRoles={['EMPLOYER', 'ADMIN']}>
                    <EmployerDashboard />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin"
                element={
                  <ProtectedRoute allowedRoles={['ADMIN']}>
                    <AdminErrorBoundary>
                      <AdminDashboard />
                    </AdminErrorBoundary>
                  </ProtectedRoute>
                }
              />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </TourProvider>
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
}

