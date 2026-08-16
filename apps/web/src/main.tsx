import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { AppRouter } from "./app/router";
import { AuthProvider } from "./features/auth/AuthProvider";
import { ErrorBoundary } from "./shared/components/ErrorBoundary";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <ErrorBoundary>
          <AppRouter />
        </ErrorBoundary>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
