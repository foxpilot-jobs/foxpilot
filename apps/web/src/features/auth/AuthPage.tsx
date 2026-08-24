import { useEffect, useState, type SubmitEventHandler } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { login, register, requestPasswordReset, resetPassword, verifyEmail } from "../../api";
import { Button } from "../../shared/ui/Button";
import { Input } from "../../shared/ui/Input";
import { Spinner } from "../../shared/ui/Spinner";
import { useAuth } from "./useAuth";
import { AuthDivider } from "./components/AuthDivider";
import { AuthLayout } from "./components/AuthLayout";
import { OAuthButton } from "./components/OAuthButton";
import { PasswordField } from "./components/PasswordField";
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
    if (mode !== "verify-email" || !token) return;
    setBusy(true);
    verifyEmail(token)
      .then((user) => {
        setUser(user);
        navigate("/app", { replace: true });
      })
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : "Unable to verify your email"),
      )
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
    if (Object.keys(validation).length > 0) return;
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
    if (!token)
      return (
        <AuthLayout
          supportingText="This link is missing or no longer valid."
          title="Invalid verification link"
        >
          <Link className="auth-secondary-link" to="/login">
            Back to sign in
          </Link>
        </AuthLayout>
      );
    if (error)
      return (
        <AuthLayout
          supportingText="We couldn't confirm this email address. The link may have expired or already been used."
          title="Verification failed"
          error={error}
        >
          <Link className="auth-secondary-link" to="/login">
            Back to sign in
          </Link>
        </AuthLayout>
      );
    return (
      <AuthLayout
        supportingText="We're confirming your email address."
        title={busy ? "Verifying your email" : "Email verification"}
      >
        <div className="auth-verifying">
          <Spinner size={20} />
          <span role="status" aria-live="polite">
            {busy ? "Verifying your email..." : "Preparing verification..."}
          </span>
        </div>
      </AuthLayout>
    );
  }
  if (isReset && !token)
    return (
      <AuthLayout
        supportingText="This password reset link is missing or no longer valid."
        title="Invalid reset link"
      >
        <Link className="auth-secondary-link" to="/login">
          Back to sign in
        </Link>
      </AuthLayout>
    );

  const title = isRegister
    ? "Create your FoxPilot account"
    : isForgot
      ? "Reset your password"
      : isReset
        ? "Create a new password"
        : "Welcome back";
  const supportingText = isRegister
    ? "Build your profile and start discovering opportunities that fit your career."
    : isForgot
      ? "Enter your email and we'll send you a link to create a new password."
      : isReset
        ? "Choose a strong password for your FoxPilot account."
        : "Continue finding opportunities that actually fit.";
  const actionLabel = busy
    ? isRegister
      ? "Creating account..."
      : isForgot
        ? "Sending reset link..."
        : isReset
          ? "Resetting password..."
          : "Signing in..."
    : isRegister
      ? "Create account"
      : isForgot
        ? "Send reset link"
        : isReset
          ? "Reset password"
          : "Sign in";
  return (
    <AuthLayout title={title} error={error} message={message} supportingText={supportingText}>
      <form className="auth-form" noValidate onSubmit={submit}>
        {!isReset && (
          <Input
            autoComplete="email"
            aria-required="true"
            error={fieldErrors.email}
            label="Email"
            placeholder="you@example.com"
            requiredIndicator
            type="email"
            value={email}
            onChange={(event) => {
              setEmail(event.target.value);
              setFieldErrors((current) => ({ ...current, email: undefined }));
            }}
          />
        )}
        {!isForgot && (
          <PasswordField
            autoComplete={isRegister || isReset ? "new-password" : "current-password"}
            error={fieldErrors.password}
            help={`Use a memorable ${MIN_PASSWORD_LENGTH}+ character passphrase.`}
            onChange={(value) => {
              setPassword(value);
              setFieldErrors((current) => ({ ...current, password: undefined }));
            }}
            value={password}
          />
        )}
        <Button disabled={busy} fullWidth loading={busy} size="lg" type="submit">
          {actionLabel}
        </Button>
      </form>
      {(mode === "login" || mode === "register") && (
        <>
          <AuthDivider />
          <OAuthButton register={isRegister} />
        </>
      )}
      {!isForgot && !isReset && (
        <p className="auth-footnote">
          {isRegister ? "Already have an account? " : "Don't have an account? "}
          <Link to={isRegister ? "/login" : "/register"}>
            {isRegister ? "Sign in" : "Create one"}
          </Link>
        </p>
      )}
      {mode === "login" && (
        <Link className="auth-forgot-link" to="/forgot-password">
          Forgot password?
        </Link>
      )}
      {(isForgot || isReset) && (
        <Link className="auth-secondary-link" to="/login">
          Back to sign in
        </Link>
      )}
    </AuthLayout>
  );
}
