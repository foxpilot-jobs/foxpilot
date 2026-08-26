import { useEffect, useMemo, useState } from "react";
import {
  getApplications,
  getJobs,
  getMatches,
  getProfile,
  updateApplication,
  type Application,
  type Job,
  type Match,
  type Profile,
} from "../../../api";
import { Alert } from "../../../shared/components/Alert";
import { Button } from "../../../shared/components/Button";
import { SkeletonCard } from "../../../shared/ui/Skeleton";
import { useAuth } from "../../auth/useAuth";
import { DashboardActions } from "../components/DashboardActions";
import { DashboardHeader } from "../components/DashboardHeader";
import { DashboardMetrics } from "../components/DashboardMetrics";
import { FilterToolbar } from "../components/FilterToolbar";
import { JobCard } from "../components/JobCard";
import { ProfilePrompt } from "../components/ProfilePrompt";
import { RecentApplications } from "../components/RecentApplications";
import { TopMatches } from "../components/TopMatches";

export function DashboardPage() {
  const { user } = useAuth();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [applications, setApplications] = useState<Record<string, Application>>({});
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [includeInactive, setIncludeInactive] = useState(false);
  const [view, setView] = useState<"matches" | "all">("matches");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [updatingJob, setUpdatingJob] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    if (!user) return;
    setLoading(true);
    setError(null);
    void Promise.allSettled([
      getJobs({ includeInactive, limit: 200 }),
      getMatches({ limit: 200 }),
      getApplications({ limit: 200 }),
      getProfile(),
    ]).then(([jobsResult, matchesResult, applicationsResult, profileResult]) => {
      const failures: string[] = [];
      if (jobsResult.status === "fulfilled") setJobs(jobsResult.value.items);
      else failures.push("jobs");
      if (matchesResult.status === "fulfilled") setMatches(matchesResult.value.items);
      else failures.push("matches");
      if (applicationsResult.status === "fulfilled") {
        setApplications(
          Object.fromEntries(
            applicationsResult.value.items.map((application) => [
              application.job_id,
              application,
            ]),
          ),
        );
      } else failures.push("applications");
      if (profileResult.status === "fulfilled") setProfile(profileResult.value);
      else failures.push("profile");
      if (failures.length > 0) setError("Some workspace data could not be loaded.");
      setLoading(false);
    });
  }, [includeInactive, reloadToken, user?.user_id]);

  const matchByJob = useMemo(
    () => new Map(matches.map((item) => [item.job_id, item.match])),
    [matches],
  );

  const hasProfileData = Boolean(profile && profile.resume_filename);

  const filteredJobs = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return jobs
      .filter((job) => {
        const jobId = job.job_id ?? "";
        const match = matchByJob.get(jobId);
        if (hasProfileData && view === "matches" && !match) return false;
        const application = applications[jobId];
        const matchesStatus = statusFilter === "all" || application?.status === statusFilter;
        const matchesQuery =
          !normalizedQuery ||
          `${job.title} ${job.company} ${job.location ?? ""}`
            .toLowerCase()
            .includes(normalizedQuery);
        return matchesStatus && matchesQuery;
      })
      .sort(
        (left, right) =>
          (matchByJob.get(right.job_id ?? "")?.match_score ?? -1) -
          (matchByJob.get(left.job_id ?? "")?.match_score ?? -1),
      );
  }, [applications, hasProfileData, jobs, matchByJob, query, statusFilter, view]);

  if (!user) return null;

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

  return (
    <main className="dashboard-overview">
      <DashboardHeader email={user.email} />
      {error && (
        <div className="dashboard-error">
          <Alert>{error}</Alert>
          <Button
            type="button"
            variant="quiet"
            onClick={() => setReloadToken((token) => token + 1)}
          >
            Try again
          </Button>
        </div>
      )}
      {loading ? (
        <DashboardSkeleton />
      ) : (
        <>
          <DashboardMetrics
            applications={Object.keys(applications).length}
            matches={matches}
            profile={hasProfileData ? profile : null}
          />
          <div className="dashboard-overview-grid">
            <TopMatches matches={matches} />
            <RecentApplications
              applications={Object.values(applications)}
              jobs={jobs}
              updatingJob={updatingJob}
              onStatusChange={(jobId, status) => void handleStatus(jobId, status)}
            />
          </div>
          <DashboardActions
            applicationCount={Object.keys(applications).length}
            hasMatches={matches.length > 0}
            hasProfile={hasProfileData}
          />
          <ProfilePrompt hasProfile={hasProfileData} resumeFilename={profile?.resume_filename} />
          <section className="dashboard-job-explorer" aria-labelledby="job-explorer-heading">
            <div className="dashboard-section-heading">
              <div>
                <p className="ui-eyebrow">All opportunities</p>
                <h2 id="job-explorer-heading">Keep exploring</h2>
              </div>
              <span className="dashboard-count">{filteredJobs.length} showing</span>
            </div>
            <div className="dashboard-views" role="tablist" aria-label="Job views">
              {hasProfileData && (
                <button
                  className={view === "matches" ? "view-tab active" : "view-tab"}
                  role="tab"
                  type="button"
                  aria-selected={view === "matches"}
                  onClick={() => setView("matches")}
                >
                  Personalized matches
                </button>
              )}
              <button
                className={view === "all" || !hasProfileData ? "view-tab active" : "view-tab"}
                role="tab"
                type="button"
                aria-selected={view === "all" || !hasProfileData}
                onClick={() => setView("all")}
              >
                All active jobs
              </button>
            </div>
            <FilterToolbar
              query={query}
              statusFilter={statusFilter}
              onQueryChange={setQuery}
              onStatusChange={setStatusFilter}
            />
            <label className="closed-jobs-toggle">
              <input
                checked={includeInactive}
                type="checkbox"
                onChange={(event) => setIncludeInactive(event.target.checked)}
              />
              Include closed roles
            </label>
            <section className="job-grid">
              {filteredJobs.map((job) => {
                const jobId = job.job_id ?? "";
                return (
                  <JobCard
                    application={applications[jobId]}
                    job={job}
                    key={jobId || `${job.company}-${job.title}`}
                    match={matchByJob.get(jobId)}
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
          </section>
        </>
      )}
    </main>
  );
}

function DashboardSkeleton() {
  return (
    <div className="dashboard-skeleton" aria-label="Loading overview" role="status">
      <div className="dashboard-metrics">
        {[1, 2, 3, 4].map((item) => (
          <SkeletonCard key={item} />
        ))}
      </div>
      <div className="dashboard-overview-grid">
        <SkeletonCard />
        <SkeletonCard />
      </div>
    </div>
  );
}
