import React from 'react';
import { BrowserRouter as Router, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Navbar from './components/Navbar';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import NewJobPage from './pages/NewJobPage';
import JobDetailPage from './pages/JobDetailPage';
import { dashboardRegistry } from './config/dashboardRegistry';

const DASHBOARD_PREFIXES = [
  '/dashboard',
  '/history',
  '/workspace',
  '/exports',
  '/demo',
  '/account',
  '/api-keys',
  '/settings',
  '/ai-integrations',
  '/system-keys',
];

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return null;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

function AppRoutes() {
  const location = useLocation();
  const { isAuthenticated } = useAuth();

  const inDashboardArea = DASHBOARD_PREFIXES.some((prefix) => location.pathname.startsWith(prefix));
  const showNavbar = !(isAuthenticated && inDashboardArea);

  return (
    <div className="min-h-screen bg-bg font-body text-textMain">
      {showNavbar ? <Navbar /> : null}
      <main className={showNavbar ? 'pt-24' : 'pt-0'}>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/jobs/new"
            element={
              <ProtectedRoute>
                <NewJobPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/jobs/:id"
            element={
              <ProtectedRoute>
                <JobDetailPage />
              </ProtectedRoute>
            }
          />
          {dashboardRegistry.map((entry) => {
            const Component = entry.component;
            const content = <Component />;
            return (
              <Route
                key={entry.key}
                path={entry.route}
                element={entry.protected ? <ProtectedRoute>{content}</ProtectedRoute> : content}
              />
            );
          })}
        </Routes>
      </main>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <AppRoutes />
      </Router>
    </AuthProvider>
  );
}

export default App;
