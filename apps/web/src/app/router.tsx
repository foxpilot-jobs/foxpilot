import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { AuthPage } from "../features/auth/AuthPage";
import { useAuth } from "../features/auth/useAuth";
import { DashboardPage } from "../features/dashboard/pages/DashboardPage";
import { JobDetailPage } from "../features/dashboard/pages/JobDetailPage";
import { ApplicationsPage } from "../features/dashboard/pages/ApplicationsPage";
import { MatchesPage } from "../features/dashboard/pages/MatchesPage";
import { ProfileSetupPage } from "../features/profile/pages/ProfileSetupPage";
import { ProfileInsightsPage } from "../features/profile/pages/ProfileInsightsPage";
import { SettingsPage } from "../features/settings/pages/SettingsPage";
import { AppLayout } from "../shared/layouts/AppLayout";
import { Spinner } from "../shared/ui/Spinner";

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
        <Route element={<AppLayout />} path="/app">
          <Route index element={<DashboardPage />} />
          <Route path="matches" element={<MatchesPage />} />
          <Route path="jobs/:jobId" element={<JobDetailPage />} />
          <Route path="applications" element={<ApplicationsPage />} />
          <Route path="profile" element={<ProfileSetupPage />} />
          <Route path="profile/insights" element={<ProfileInsightsPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
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
    <main className="auth-loading-screen" aria-label="Loading FoxPilot" role="status">
      <div className="auth-loading-card">
        <span className="auth-loading-mark">
          <img src="/brand/foxpilot-mark.png" alt="" />
        </span>
        <div className="auth-loading-copy">
          <strong>FoxPilot</strong>
          <span>Preparing your workspace</span>
        </div>
        <Spinner label="Loading" size={20} />
      </div>
    </main>
  );
}
