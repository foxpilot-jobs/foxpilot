import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  getAuthUser,
  getApplications,
  getJobs,
  getMatches,
  login,
  logout,
  register,
  requestPasswordReset,
  resetPassword,
  verifyEmail,
  updateApplication,
  type Application,
  type AuthUser,
  type Job,
  type Match,
} from "./api";

const statuses: Array<Application["status"]> = [
  "saved",
  "applied",
  "interviewing",
  "rejected",
  "offered",
];

function formatStatus(status: string) {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function AuthScreen({ onAuthenticated }: { onAuthenticated: (user: AuthUser) => void }) {
  const searchToken = new URLSearchParams(window.location.search).get("token");
  const route = window.location.pathname;
  const verification = route === "/verify-email" && Boolean(searchToken);
  const reset = route === "/reset-password" && Boolean(searchToken);
  const [registering, setRegistering] = useState(false);
  const [forgotten, setForgotten] = useState(route === "/forgot-password");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!verification) {
      return;
    }
    verifyEmail(searchToken ?? "")
      .then(onAuthenticated)
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Unable to verify your email");
      });
  }, [onAuthenticated, searchToken, verification]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const user = reset
        ? await resetPassword(searchToken ?? "", password)
        : registering
          ? await register(email, password)
          : await login(email, password);
      if (registering && !user.session_created) {
        setMessage("Check your email to verify your FoxPilot account before signing in.");
        return;
      }
      onAuthenticated(user);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to authenticate");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-shell">
      <p className="eyebrow accent">FOXPILOT</p>
      <h1>
        {verification
          ? "Verifying your email..."
          : reset
            ? "Choose a new password."
            : forgotten
              ? "Reset your FoxPilot password."
              : registering
                ? "Make your next move clearer."
                : "Welcome back, career navigator."}
      </h1>
      <p className="hero-copy">
        Keep your matches, decisions, and application history private to you.
      </p>
      {verification ? null : forgotten && !reset ? (
        <form
          className="auth-form"
          onSubmit={async (event) => {
            event.preventDefault();
            setBusy(true);
            setError(null);
            try {
              await requestPasswordReset(email);
              setMessage("If an account exists for that email, a reset link is on its way.");
            } catch (reason: unknown) {
              setError(reason instanceof Error ? reason.message : "Unable to request a reset");
            } finally {
              setBusy(false);
            }
          }}
        >
          <label>
            Email
            <input
              autoComplete="email"
              required
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          {message && <div className="success-card">{message}</div>}
          {error && <div className="error-card">{error}</div>}
          <button className="primary-button" disabled={busy} type="submit">
            {busy ? "Working..." : "Send reset link"}
          </button>
        </form>
      ) : (
        <form className="auth-form" onSubmit={submit}>
          <label>
            Email
            <input
              autoComplete="email"
              required
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label>
            Password
            <input
              autoComplete={registering || reset ? "new-password" : "current-password"}
              minLength={12}
              required
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          {error && <div className="error-card">{error}</div>}
          {message && <div className="success-card">{message}</div>}
          <button className="primary-button" disabled={busy} type="submit">
            {busy
              ? "Working..."
              : reset
                ? "Reset password"
                : registering
                  ? "Create account"
                  : "Sign in"}
          </button>
        </form>
      )}
      {!verification && !reset && (
        <button
          className="text-button"
          type="button"
          onClick={() => {
            setForgotten((value) => !value);
            setRegistering(false);
            setMessage(null);
          }}
        >
          {forgotten ? "Back to sign in" : "Forgot your password?"}
        </button>
      )}
      {!verification && !forgotten && !reset && (
        <button
          className="text-button"
          type="button"
          onClick={() => setRegistering((value) => !value)}
        >
          {registering ? "Already have an account? Sign in" : "New to FoxPilot? Create an account"}
        </button>
      )}
    </main>
  );
}

export function App() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [applications, setApplications] = useState<Record<string, Application>>({});
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [error, setError] = useState<string | null>(null);
  const [updatingJob, setUpdatingJob] = useState<string | null>(null);

  useEffect(() => {
    getAuthUser()
      .then(setUser)
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Unable to check your session");
      })
      .finally(() => setAuthLoading(false));
  }, []);

  useEffect(() => {
    if (!user) {
      return;
    }
    Promise.all([getJobs(), getMatches(), getApplications()])
      .then(([loadedJobs, loadedMatches, loadedApplications]) => {
        setJobs(loadedJobs);
        setMatches(loadedMatches);
        setApplications(
          Object.fromEntries(
            loadedApplications.map((application) => [application.job_id, application]),
          ),
        );
      })
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Unable to load your shortlist");
      });
  }, [user]);

  const filteredJobs = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return jobs.filter((job) => {
      const application = applications[job.job_id ?? ""];
      const matchesStatus = statusFilter === "all" || application?.status === statusFilter;
      const matchesQuery =
        !normalizedQuery ||
        `${job.title} ${job.company} ${job.location ?? ""}`.toLowerCase().includes(normalizedQuery);
      return matchesStatus && matchesQuery;
    });
  }, [applications, jobs, query, statusFilter]);

  if (authLoading) {
    return (
      <main className="auth-shell">
        <p className="eyebrow">FOXPILOT</p>
        <h1>Preparing your workspace...</h1>
      </main>
    );
  }

  if (!user) {
    return <AuthScreen onAuthenticated={setUser} />;
  }

  const matchByJob = new Map(matches.map((item) => [item.job_id, item.match]));

  async function handleStatus(jobId: string, status: Application["status"]) {
    setUpdatingJob(jobId);
    setError(null);
    try {
      const application = await updateApplication(jobId, status);
      setApplications((current) => ({ ...current, [jobId]: application }));
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to update application");
    } finally {
      setUpdatingJob(null);
    }
  }

  const savedCount = Object.values(applications).filter((item) => item.status === "saved").length;
  const appliedCount = Object.values(applications).filter(
    (item) => item.status === "applied",
  ).length;

  return (
    <main className="shell">
      <nav className="topbar">
        <div className="brand-mark">FP</div>
        <div>
          <p className="eyebrow">FOXPILOT</p>
          <p className="muted">A sharper shortlist for your next move</p>
        </div>
        <div className="account-actions">
          <span className="muted">{user.email}</span>
          {user.user_id !== "local-user" && (
            <button
              className="ghost-button"
              type="button"
              onClick={() => void logout().then(() => setUser(null))}
            >
              Sign out
            </button>
          )}
        </div>
      </nav>

      <section className="hero">
        <div>
          <p className="eyebrow accent">TODAY&apos;S SIGNAL</p>
          <h1>Spend less time searching. Spend more time choosing.</h1>
          <p className="hero-copy">
            Your local agent found the opportunities most aligned with your profile. Review the
            evidence, track your decisions, and keep momentum.
          </p>
        </div>
        <div className="signal-card">
          <span className="signal-number">{jobs.length}</span>
          <span className="muted">target roles ready</span>
        </div>
      </section>

      {error && (
        <div className="error-card">
          {error}. Check that the API is running and authenticated correctly.
        </div>
      )}

      <section className="metrics" aria-label="Application summary">
        <div>
          <span className="metric-value">{matches.length}</span>
          <span className="metric-label">analyzed matches</span>
        </div>
        <div>
          <span className="metric-value">{savedCount}</span>
          <span className="metric-label">saved to revisit</span>
        </div>
        <div>
          <span className="metric-value">{appliedCount}</span>
          <span className="metric-label">applications sent</span>
        </div>
      </section>

      <section className="section-heading">
        <div>
          <p className="eyebrow">SHORTLIST</p>
          <h2>Worth a closer look</h2>
        </div>
        <span className="count-pill">{filteredJobs.length} showing</span>
      </section>

      <section className="toolbar" aria-label="Shortlist filters">
        <input
          aria-label="Search jobs"
          placeholder="Search title, company, location"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <div className="filter-tabs">
          {(["all", ...statuses] as const).map((status) => (
            <button
              className={statusFilter === status ? "active" : ""}
              key={status}
              type="button"
              onClick={() => setStatusFilter(status)}
            >
              {status === "all" ? "All" : formatStatus(status)}
            </button>
          ))}
        </div>
      </section>

      <section className="job-grid">
        {filteredJobs.map((job) => {
          const jobId = job.job_id ?? "";
          const match = matchByJob.get(jobId);
          const application = applications[jobId];
          return (
            <article className="job-card" key={jobId || `${job.company}-${job.title}`}>
              <div className="card-topline">
                <span className="source-label">{job.source ?? "JOB SOURCE"}</span>
                {match && <span className="score">{match.match_score}% fit</span>}
              </div>
              <h3>{job.title}</h3>
              <p className="company">{job.company}</p>
              <p className="location">{job.location || "Location not specified"}</p>
              {match && <p className="reason">{match.reasons[0] ?? match.experience_match}</p>}
              {match && (
                <details className="evidence">
                  <summary>Why this match</summary>
                  <div className="evidence-grid">
                    <div>
                      <strong>Strengths</strong>
                      <span>
                        {match.matching_skills.join(", ") || "Profile alignment identified"}
                      </span>
                    </div>
                    <div>
                      <strong>Gaps</strong>
                      <span>{match.missing_skills.join(", ") || "No major gaps found"}</span>
                    </div>
                    <div>
                      <strong>Concerns</strong>
                      <span>{match.concerns.join(", ") || "None flagged"}</span>
                    </div>
                  </div>
                </details>
              )}
              <div className="card-actions">
                {job.url && (
                  <a href={job.url} target="_blank" rel="noreferrer">
                    View role
                  </a>
                )}
                <select
                  aria-label={`Application status for ${job.title}`}
                  value={application?.status ?? ""}
                  disabled={updatingJob === jobId}
                  onChange={(event) =>
                    handleStatus(jobId, event.target.value as Application["status"])
                  }
                >
                  <option value="">Track status</option>
                  {statuses.map((status) => (
                    <option key={status} value={status}>
                      {formatStatus(status)}
                    </option>
                  ))}
                </select>
              </div>
            </article>
          );
        })}
      </section>
      {filteredJobs.length === 0 && (
        <div className="empty-state">
          <strong>No roles match this view.</strong>
          <span>Try clearing the search or choosing All.</span>
        </div>
      )}
    </main>
  );
}
