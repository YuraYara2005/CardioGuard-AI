import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './store/AuthContext';
import LoginPage from './pages/LoginPage';
import DoctorDashboard from './pages/DoctorDashboard';
import PatientPortal from './pages/PatientPortal';
import type { ReactNode } from 'react';

// ── Protected route wrapper ───────────────────────────────────────────────────
function Protected({ children, role }: { children: ReactNode; role?: string }) {
  const { user, isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (role && user?.role !== role) {
    // Wrong role → redirect to the correct portal
    return <Navigate to={user?.role === 'Doctor' ? '/dashboard' : '/portal'} replace />;
  }
  return <>{children}</>;
}

// ── Role-aware redirect from "/" ──────────────────────────────────────────────
function RootRedirect() {
  const { user, isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <Navigate to={user?.role === 'Doctor' ? '/dashboard' : '/portal'} replace />;
}

// ── App shell ─────────────────────────────────────────────────────────────────
function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/dashboard/*"
        element={
          <Protected role="Doctor">
            <DoctorDashboard />
          </Protected>
        }
      />
      <Route
        path="/portal/*"
        element={
          <Protected role="Patient">
            <PatientPortal />
          </Protected>
        }
      />
      <Route path="/" element={<RootRedirect />} />
      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
