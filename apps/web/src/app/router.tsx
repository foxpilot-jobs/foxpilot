import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { AuthPage } from "../features/auth/AuthPage";
import { useAuth } from "../features/auth/useAuth";
import { DashboardPage } from "../features/dashboard/pages/DashboardPage";
import { JobDetailPage } from "../features/dashboard/pages/JobDetailPage";
import { MatchesPage } from "../features/dashboard/pages/MatchesPage";
import { ArchitecturePlaceholderPage } from "../features/navigation/pages/ArchitecturePlaceholderPage";
import { ProfileSetupPage } from "../features/profile/pages/ProfileSetupPage";
import { AppLayout } from "../shared/layouts/AppLayout";

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
          <Route
            path="applications"
            element={
              <ArchitecturePlaceholderPage
                description="Track your application pipeline in one focused workspace."
                title="Applications"
              />
            }
          />
          <Route path="profile" element={<ProfileSetupPage />} />
          <Route
            path="profile/insights"
            element={
              <ArchitecturePlaceholderPage
                description="Profile strengths, gaps, and recommendations will live here."
                title="Profile insights"
              />
            }
          />
          <Route
            path="settings"
            element={
              <ArchitecturePlaceholderPage
                description="Account and appearance preferences will live here."
                title="Settings"
              />
            }
          />
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
    <main className="auth-shell">
      <div className="auth-brand">
        <img src="/brand/foxpilot-mark.png" alt="FoxPilot" />
        <span className="eyebrow">FOXPILOT</span>
      </div>
      <h1>Preparing your workspace...</h1>
    </main>
  );
}
