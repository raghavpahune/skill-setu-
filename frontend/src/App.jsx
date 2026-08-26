import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import Landing from './pages/Landing';
import GovernmentDashboard from './pages/GovernmentDashboard';
import DistrictPlan from './pages/DistrictPlan';
import InstituteDashboard from './pages/InstituteDashboard';
import StudentDashboard from './pages/StudentDashboard';
import CopilotPage from './pages/CopilotPage';
import EmployerDashboard from './pages/EmployerDashboard';

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
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}
