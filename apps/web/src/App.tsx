import { useEffect, useMemo, useState } from "react";
import {
  getApplications,
  getJobs,
  getMatches,
  updateApplication,
  type Application,
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

export function App() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [applications, setApplications] = useState<Record<string, Application>>({});
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [error, setError] = useState<string | null>(null);
  const [updatingJob, setUpdatingJob] = useState<string | null>(null);

  useEffect(() => {
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
  }, []);

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
        <button className="ghost-button" type="button">
          Settings
        </button>
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
