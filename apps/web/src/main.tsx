import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { AppRouter } from "./app/router";
import { AuthProvider } from "./features/auth/AuthProvider";
import { ErrorBoundary } from "./shared/components/ErrorBoundary";
import "@fontsource-variable/inter";
import "@fontsource-variable/manrope";
import "./styles.css";
import { ThemeProvider } from "./shared/ui/ThemeProvider";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <ThemeProvider>
          <ErrorBoundary>
            <AppRouter />
          </ErrorBoundary>
        </ThemeProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
