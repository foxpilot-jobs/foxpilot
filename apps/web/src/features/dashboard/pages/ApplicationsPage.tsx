import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  getApplications,
  getJobs,
  getMatches,
  updateApplication,
  type Application,
  type Job,
  type Match,
} from "../../../api";
import { Alert } from "../../../shared/ui/Alert";
import { Button } from "../../../shared/ui/Button";
import { EmptyState } from "../../../shared/ui/EmptyState";
import { ErrorState } from "../../../shared/ui/ErrorState";
import { useAuth } from "../../auth/useAuth";
import { ApplicationFilters } from "../components/applications/ApplicationFilters";
import { ApplicationHeader } from "../components/applications/ApplicationHeader";
import { ApplicationListSkeleton } from "../components/applications/ApplicationListSkeleton";
import { ApplicationPipeline } from "../components/applications/ApplicationPipeline";
import { ApplicationSummary } from "../components/applications/ApplicationSummary";

export function ApplicationsPage() {
  const { user } = useAuth();
  const [applications, setApplications] = useState<Application[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [updateError, setUpdateError] = useState(false);
  const [updatingJob, setUpdatingJob] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [retryToken, setRetryToken] = useState(0);

  useEffect(() => {
    if (!user) return;
    setLoading(true);
    setLoadError(false);
    void Promise.allSettled([getApplications(), getMatches(), getJobs(true)]).then(
      ([applicationsResult, matchesResult, jobsResult]) => {
        if (applicationsResult.status === "fulfilled") setApplications(applicationsResult.value);
        else setLoadError(true);
        if (matchesResult.status === "fulfilled") setMatches(matchesResult.value);
        if (jobsResult.status === "fulfilled") setJobs(jobsResult.value);
        setLoading(false);
      },
    );
  }, [retryToken, user]);

  const visibleApplications = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return applications.filter((application) => {
      const job = jobs.find((item) => item.job_id === application.job_id);
      const title = application.title ?? job?.title ?? "";
      const company = application.company ?? job?.company ?? "";
      return (
        (status === "all" || application.status === status) &&
        (!normalizedQuery || `${title} ${company}`.toLowerCase().includes(normalizedQuery))
      );
    });
  }, [applications, jobs, query, status]);

  if (!user) return null;
  if (loading)
    return (
      <main className="applications-page">
        <ApplicationHeader />
        <ApplicationListSkeleton />
      </main>
    );
  if (loadError)
    return (
      <main className="applications-state">
        <ErrorState
          action={
            <Button type="button" onClick={() => setRetryToken((token) => token + 1)}>
              Try again
            </Button>
          }
          description="We couldn't load your application pipeline. Please try again."
          title="Couldn't load your applications"
        />
      </main>
    );
  if (applications.length === 0)
    return (
      <main className="applications-page">
        <ApplicationHeader />
        <EmptyState
          action={
            <Link className="ui-button ui-button-primary ui-button-md" to="/app/matches">
              Explore matches
            </Link>
          }
          description="Save a role from Matches when you're ready to keep track of it."
          title="Your application pipeline is empty"
        />
      </main>
    );

  async function handleStatus(jobId: string, nextStatus: Application["status"]) {
    setUpdatingJob(jobId);
    setNotice(null);
    setUpdateError(false);
    try {
      const updated = await updateApplication(jobId, nextStatus);
      setApplications((current) =>
        current.map((application) => (application.job_id === jobId ? updated : application)),
      );
      setNotice("Application status updated.");
    } catch {
      setUpdateError(true);
    } finally {
      setUpdatingJob(null);
    }
  }

  const matchByJob = new Map(matches.map((item) => [item.job_id, item]));
  return (
    <main className="applications-page">
      <ApplicationHeader />
      {notice && (
        <div className="applications-notice" role="status" aria-live="polite">
          {notice}
        </div>
      )}
      {updateError && (
        <div className="applications-update-error">
          <Alert variant="error">
            Your status could not be updated. Your previous status is unchanged.
          </Alert>
        </div>
      )}
      <ApplicationSummary applications={applications} />
      <ApplicationFilters
        onQueryChange={setQuery}
        onStatusChange={setStatus}
        query={query}
        status={status}
      />
      {visibleApplications.length === 0 ? (
        <EmptyState
          action={
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setQuery("");
                setStatus("all");
              }}
            >
              Clear search
            </Button>
          }
          description={
            query
              ? "Try a broader search or clear the current search."
              : `No ${status} roles yet. Keep going, your next opportunity can start in Matches.`
          }
          title={query ? "No applications found" : `No ${status} roles yet`}
        />
      ) : (
        <ApplicationPipeline
          applications={visibleApplications}
          jobs={jobs}
          matches={matches}
          onStatusChange={handleStatus}
          statusFilter={status}
          updatingJob={updatingJob}
        />
      )}
      {visibleApplications.length > 0 && (
        <p className="applications-note">
          {matchByJob.size > 0
            ? "Match scores are shown when FoxPilot has evaluated the role."
            : "Track your progress as you move each opportunity forward."}
        </p>
      )}
    </main>
  );
}
