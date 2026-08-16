import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  getProfile,
  getApplications,
  getJobs,
  getMatches,
  updateApplication,
  type Application,
  type Job,
  type Match,
  type Profile,
} from "../../../api";
import { Alert } from "../../../shared/components/Alert";
import { Button } from "../../../shared/components/Button";
import { LoadingState } from "../../../shared/components/LoadingState";
import { useAuth } from "../../auth/useAuth";
import { FilterToolbar } from "../components/FilterToolbar";
import { JobCard } from "../components/JobCard";
import { MetricsSummary } from "../components/MetricsSummary";

export function DashboardPage() {
  const { signOut, user } = useAuth();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [applications, setApplications] = useState<Record<string, Application>>({});
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [updatingJob, setUpdatingJob] = useState<string | null>(null);

  useEffect(() => {
    if (!user) {
      return;
    }
    setLoading(true);
    Promise.all([getJobs(), getMatches(), getApplications(), getProfile()])
      .then(([loadedJobs, loadedMatches, loadedApplications, loadedProfile]) => {
        setJobs(loadedJobs);
        setMatches(loadedMatches);
        setApplications(
          Object.fromEntries(
            loadedApplications.map((application) => [application.job_id, application]),
          ),
        );
        setProfile(loadedProfile);
      })
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Unable to load your shortlist");
      })
      .finally(() => setLoading(false));
  }, [user]);

  const matchByJob = useMemo(
    () => new Map(matches.map((item) => [item.job_id, item.match])),
    [matches],
  );

  const filteredJobs = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return jobs
      .filter((job) => {
        const jobId = job.job_id ?? "";
        const match = matchByJob.get(jobId);
        if (!match) return false;
        const application = applications[job.job_id ?? ""];
        const matchesStatus = statusFilter === "all" || application?.status === statusFilter;
        const matchesQuery =
          !normalizedQuery ||
          `${job.title} ${job.company} ${job.location ?? ""}`
            .toLowerCase()
            .includes(normalizedQuery);
        return matchesStatus && matchesQuery;
      })
      .sort((left, right) => {
        const leftScore = matchByJob.get(left.job_id ?? "")?.match_score ?? -1;
        const rightScore = matchByJob.get(right.job_id ?? "")?.match_score ?? -1;
        return rightScore - leftScore;
      });
  }, [applications, jobs, matchByJob, query, statusFilter]);

  const matchedJobs = useMemo(
    () => jobs.filter((job) => matchByJob.has(job.job_id ?? "")),
    [jobs, matchByJob],
  );
  const matchedJobIds = useMemo(
    () => new Set(matchedJobs.map((job) => job.job_id ?? "")),
    [matchedJobs],
  );

  if (!user) {
    return null;
  }

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

  const savedCount = Object.values(applications).filter(
    (item) => item.status === "saved" && matchedJobIds.has(item.job_id),
  ).length;
  const appliedCount = Object.values(applications).filter(
    (item) => item.status === "applied" && matchedJobIds.has(item.job_id),
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
          <span className="account-email">{user.email}</span>
          <Button
            variant="quiet"
            type="button"
            onClick={() =>
              void signOut().catch((reason: unknown) =>
                setError(reason instanceof Error ? reason.message : "Unable to sign out"),
              )
            }
          >
            Sign out
          </Button>
          <Link className="profile-link" to="/app/profile">
            Profile
          </Link>
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
          <span className="signal-number">{matchedJobs.length}</span>
          <span className="muted">matched roles ready</span>
        </div>
      </section>

      {error && (
        <Alert>{`${error}. Check that the API is running and authenticated correctly.`}</Alert>
      )}

      {!loading && profile === null && (
        <section className="profile-banner">
          <div>
            <p className="eyebrow accent">START HERE</p>
            <h2>Upload your resume to unlock match scores.</h2>
            <p>
              FoxPilot will use your experience, skills, and target roles to explain what fits and
              where the gaps are.
            </p>
          </div>
          <Link className="primary-button" to="/app/profile">
            Set up profile
          </Link>
        </section>
      )}

      {loading ? (
        <LoadingState label="Loading your shortlist..." />
      ) : (
        <>
          <MetricsSummary applied={appliedCount} matches={matchedJobs.length} saved={savedCount} />

          <section className="section-heading">
            <div>
              <p className="eyebrow">SHORTLIST</p>
              <h2>Worth a closer look</h2>
            </div>
            <span className="count-pill">{filteredJobs.length} showing</span>
          </section>

          <FilterToolbar
            query={query}
            statusFilter={statusFilter}
            onQueryChange={setQuery}
            onStatusChange={setStatusFilter}
          />

          <section className="job-grid">
            {filteredJobs.map((job) => {
              const jobId = job.job_id ?? "";
              const match = matchByJob.get(jobId);
              const application = applications[jobId];
              return (
                <JobCard
                  application={application}
                  job={job}
                  key={jobId || `${job.company}-${job.title}`}
                  match={match}
                  updating={updatingJob === jobId}
                  onStatusChange={(status) => void handleStatus(jobId, status)}
                />
              );
            })}
          </section>
          {filteredJobs.length === 0 && (
            <div className="empty-state">
              <strong>No roles match this view.</strong>
              <span>Try clearing the search or choosing All.</span>
            </div>
          )}
        </>
      )}
    </main>
  );
}
