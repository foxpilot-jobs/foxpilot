import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Alert } from "../../../shared/ui/Alert";

export function AuthLayout({
  children,
  error,
  message,
  supportingText,
  title,
  titleId = "auth-page-title",
}: {
  children?: ReactNode;
  error?: string | null;
  message?: string | null;
  supportingText?: string;
  title: string;
  titleId?: string;
}) {
  return (
    <main aria-labelledby={titleId} className="auth-shell">
      <aside className="auth-brand-panel">
        <Link className="auth-brand" to="/login">
          <span className="auth-brand-mark">
            <img src="/brand/foxpilot-mark.png" alt="" />
          </span>
          <span className="auth-brand-name">FoxPilot</span>
        </Link>
        <div className="auth-brand-copy">
          <p className="ui-eyebrow">Your career copilot</p>
          <h2>Navigate your next move with confidence.</h2>
          <p>
            Find opportunities that fit your experience, understand why they fit, and make better
            career decisions.
          </p>
          <ul>
            <li>Smarter job matching</li>
            <li>Evidence-backed recommendations</li>
            <li>One place for your career search</li>
          </ul>
        </div>
        <span className="auth-brand-accent" aria-hidden="true" />
      </aside>
      <section className="auth-panel">
        <div className="auth-panel-inner">
          <div className="auth-mobile-brand">
            <Link className="auth-brand" to="/login">
              <span className="auth-brand-mark">
                <img src="/brand/foxpilot-mark.png" alt="" />
              </span>
              <span className="auth-brand-name">FoxPilot</span>
            </Link>
          </div>
          <div className="auth-heading">
            <h1 id={titleId}>{title}</h1>
            {supportingText && <p>{supportingText}</p>}
          </div>
          {error && (
            <div className="auth-status">
              <Alert variant="error">{error}</Alert>
            </div>
          )}
          {message && (
            <div className="auth-status">
              <Alert title="Almost there" variant="success">
                {message}
              </Alert>
            </div>
          )}
          {children}
        </div>
      </section>
    </main>
  );
}
