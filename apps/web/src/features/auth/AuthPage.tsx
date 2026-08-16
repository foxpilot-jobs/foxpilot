import { useEffect, useState, type SubmitEventHandler } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { login, register, requestPasswordReset, resetPassword, verifyEmail } from "../../api";
import { Alert } from "../../shared/components/Alert";
import { Button } from "../../shared/components/Button";
import { TextField } from "../../shared/components/TextField";
import { useAuth } from "./useAuth";
import {
  MIN_PASSWORD_LENGTH,
  validateCredentials,
  validateEmail,
  type CredentialErrors,
} from "./validation";

export function AuthPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const token = new URLSearchParams(location.search).get("token");
  const route = location.pathname;
  const oauthError = new URLSearchParams(location.search).get("oauth_error");
  const mode = route.slice(1) as
    "login" | "register" | "forgot-password" | "reset-password" | "verify-email";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(
    oauthError ? "Google sign-in could not be completed. Please try again." : null,
  );
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<CredentialErrors>({});
  const isRegister = mode === "register";
  const isForgot = mode === "forgot-password";
  const isReset = mode === "reset-password";

  useEffect(() => {
    if (mode !== "verify-email" || !token) {
      return;
    }
    setBusy(true);
    verifyEmail(token)
      .then((user) => {
        setUser(user);
        navigate("/app", { replace: true });
      })
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Unable to verify your email");
      })
      .finally(() => setBusy(false));
  }, [mode, navigate, setUser, token]);

  const submit: SubmitEventHandler<HTMLFormElement> = async (event) => {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setFieldErrors({});
    const validation: CredentialErrors = isForgot
      ? (() => {
          const emailError = validateEmail(email);
          return emailError ? { email: emailError } : {};
        })()
      : isReset
        ? (() => {
            const passwordError = validateCredentials("reset@example.com", password).password;
            return passwordError ? { password: passwordError } : {};
          })()
        : validateCredentials(email, password);
    setFieldErrors(validation);
    if (Object.keys(validation).length > 0) {
      return;
    }

    if (isForgot) {
      setBusy(true);
      try {
        await requestPasswordReset(email);
        setMessage("If an account exists for that email, a reset link is on its way.");
      } catch (reason: unknown) {
        setError(reason instanceof Error ? reason.message : "Unable to request a reset");
      } finally {
        setBusy(false);
      }
      return;
    }

    setBusy(true);
    try {
      const user =
        mode === "register"
          ? await register(email, password)
          : mode === "reset-password"
            ? await resetPassword(token ?? "", password)
            : await login(email, password);
      if (!user.session_created) {
        setMessage("Check your email to verify your FoxPilot account before signing in.");
        return;
      }
      setUser(user);
      navigate("/app", { replace: true });
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to authenticate");
    } finally {
      setBusy(false);
    }
  };

  if (mode === "verify-email") {
    return (
      <AuthLayout title={busy ? "Verifying your email..." : "Email verification"} error={error} />
    );
  }

  const title = isRegister
    ? "Make your next move clearer."
    : isForgot
      ? "Reset your FoxPilot password."
      : isReset
        ? "Choose a new password."
        : "Welcome back, career navigator.";

  return (
    <AuthLayout title={title} error={error} message={message}>
      <form className="auth-form" noValidate onSubmit={submit}>
        {!isReset && (
          <TextField
            autoComplete="email"
            aria-required="true"
            error={fieldErrors.email}
            label="Email"
            type="email"
            value={email}
            onChange={(event) => {
              setEmail(event.target.value);
              setFieldErrors((current) => ({ ...current, email: undefined }));
            }}
          />
        )}
        {!isForgot && (
          <TextField
            autoComplete={isRegister || isReset ? "new-password" : "current-password"}
            aria-required="true"
            error={fieldErrors.password}
            help={`Use a memorable ${MIN_PASSWORD_LENGTH}+ character passphrase.`}
            label="Password"
            type="password"
            value={password}
            onChange={(event) => {
              setPassword(event.target.value);
              setFieldErrors((current) => ({ ...current, password: undefined }));
            }}
          />
        )}
        <Button disabled={busy} type="submit">
          {busy
            ? "Working..."
            : isRegister
              ? "Create account"
              : isForgot
                ? "Send reset link"
                : isReset
                  ? "Reset password"
                  : "Sign in"}
        </Button>
      </form>
      {(mode === "login" || mode === "register") && (
        <>
          <div className="auth-divider">
            <span>or continue with</span>
          </div>
          <a className="google-button" href="/api/v1/auth/google/start">
            <span className="google-mark" aria-hidden="true">
              G
            </span>
            {mode === "register" ? "Sign up with Google" : "Continue with Google"}
          </a>
        </>
      )}
      {!isForgot && !isReset && (
        <button
          className="text-button"
          type="button"
          onClick={() => navigate(isRegister ? "/login" : "/register")}
        >
          {isRegister ? "Already have an account? Sign in" : "New to FoxPilot? Create an account"}
        </button>
      )}
      {mode === "login" && (
        <button className="text-button" type="button" onClick={() => navigate("/forgot-password")}>
          Forgot your password?
        </button>
      )}
    </AuthLayout>
  );
}

function AuthLayout({
  children,
  error,
  message,
  title,
}: {
  children?: React.ReactNode;
  error?: string | null;
  message?: string | null;
  title: string;
}) {
  return (
    <main className="auth-shell">
      <p className="eyebrow accent">FOXPILOT</p>
      <h1>{title}</h1>
      <p className="hero-copy">
        Keep your matches, decisions, and application history private to you.
      </p>
      {error && <Alert>{error}</Alert>}
      {message && <Alert tone="success">{message}</Alert>}
      {children}
    </main>
  );
}
