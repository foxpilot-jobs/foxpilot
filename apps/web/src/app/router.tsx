import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { AuthPage } from "../features/auth/AuthPage";
import { useAuth } from "../features/auth/useAuth";
import { DashboardPage } from "../features/dashboard/pages/DashboardPage";
import { ProfileSetupPage } from "../features/profile/pages/ProfileSetupPage";

export function AppRouter() {
  return (
    <Routes>
      <Route element={<PublicRoute />}>
        <Route path="/login" element={<AuthPage />} />
        <Route path="/register" element={<AuthPage />} />
        <Route path="/forgot-password" element={<AuthPage />} />
        <Route path="/reset-password" element={<AuthPage />} />
        <Route path="/verify-email" element={<AuthPage />} />
      </Route>
      <Route element={<ProtectedRoute />}>
        <Route path="/app" element={<DashboardPage />} />
        <Route path="/app/profile" element={<ProfileSetupPage />} />
      </Route>
      <Route path="*" element={<Navigate replace to="/app" />} />
    </Routes>
  );
}

function PublicRoute() {
  const { loading, user } = useAuth();
  if (loading) {
    return <LoadingScreen />;
  }
  return user ? <Navigate replace to="/app" /> : <Outlet />;
}

function ProtectedRoute() {
  const { loading, user } = useAuth();
  if (loading) {
    return <LoadingScreen />;
  }
  return user ? <Outlet /> : <Navigate replace to="/login" />;
}

function LoadingScreen() {
  return (
    <main className="auth-shell">
      <p className="eyebrow">FOXPILOT</p>
      <h1>Preparing your workspace...</h1>
    </main>
  );
}
