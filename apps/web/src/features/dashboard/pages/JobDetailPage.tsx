import { ArrowLeft, ExternalLink, MapPin, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  getApplications,
  getJobs,
  getMatches,
  updateApplication,
  type Application,
  type Job,
  type Match,
} from "../../../api";
import { Button } from "../../../shared/ui/Button";
import { Avatar } from "../../../shared/ui/Avatar";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../../shared/ui/Card";
import { EmptyState } from "../../../shared/ui/EmptyState";
import { ErrorState } from "../../../shared/ui/ErrorState";
import { Skeleton } from "../../../shared/ui/Skeleton";
import { Toast } from "../../../shared/ui/Toast";
import { useAuth } from "../../auth/useAuth";
import { ApplicationStatusSelect } from "../components/ApplicationStatusSelect";
import { MatchGapAnalysis } from "../components/matches/MatchGapAnalysis";
import { MatchReasons } from "../components/matches/MatchReasons";
import { MatchScore } from "../components/matches/MatchScore";

export function JobDetailPage() {
  const { jobId = "" } = useParams();
  const { user } = useAuth();
  const [job, setJob] = useState<Job | null>(null);
  const [match, setMatch] = useState<Match["match"] | null>(null);
  const [application, setApplication] = useState<Application | undefined>();
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [statusError, setStatusError] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [retryToken, setRetryToken] = useState(0);

  useEffect(() => {
    if (!user || !jobId) return;
    let active = true;
    setLoading(true);
    setLoadError(false);
    setNotFound(false);
    void Promise.allSettled([getMatches(), getJobs(true), getApplications()]).then(
      ([matchesResult, jobsResult, applicationsResult]) => {
        if (!active) return;
        const foundMatch =
          matchesResult.status === "fulfilled"
            ? matchesResult.value.find((item) => item.job_id === jobId)
            : undefined;
        const foundJob =
          foundMatch?.job ??
          (jobsResult.status === "fulfilled"
            ? jobsResult.value.find((item) => item.job_id === jobId)
            : undefined);
        setJob(foundJob ?? null);
        setMatch(foundMatch?.match ?? null);
        setApplication(
          applicationsResult.status === "fulfilled"
            ? applicationsResult.value.find((item) => item.job_id === jobId)
            : undefined,
        );
        setNotFound(
          !foundJob && matchesResult.status === "fulfilled" && jobsResult.status === "fulfilled",
        );
        setLoadError(
          !foundJob && (matchesResult.status === "rejected" || jobsResult.status === "rejected"),
        );
        setLoading(false);
      },
    );
    return () => {
      active = false;
    };
  }, [jobId, retryToken, user?.user_id]);

  async function handleStatus(status: Application["status"]) {
    setUpdating(true);
    setNotice(null);
    setStatusError(false);
    try {
      const updatedApplication = await updateApplication(jobId, status);
      setApplication(updatedApplication);
      setNotice("Application status updated.");
    } catch {
      setStatusError(true);
    } finally {
      setUpdating(false);
    }
  }

  if (!user) return null;
  if (loading) return <JobDetailSkeleton />;
  if (loadError && !job)
    return <JobDetailError onRetry={() => setRetryToken((token) => token + 1)} />;
  if (notFound || !job) return <JobNotFound />;

  const sourceRecord = job.sources?.find((item) => item.url);
  const listing = sourceRecord?.url ?? job.url;
  const source =
    sourceRecord?.source ?? job.sources?.[0]?.source ?? job.source ?? "original listing";
  return (
    <main className="job-detail-page">
      <Link className="job-detail-back" to="/app/matches">
        <ArrowLeft size={16} aria-hidden="true" />
        Back to matches
      </Link>
      <JobHeader job={job} match={match} listing={listing} source={source} />
      {notice && (
        <div className="job-detail-notice">
          <Toast title="Updated" variant="success" onDismiss={() => setNotice(null)}>
            {notice}
          </Toast>
        </div>
      )}
      {statusError && (
        <div className="job-detail-inline-error">
          <ErrorState
            action={
              <Button type="button" variant="outline" onClick={() => setStatusError(false)}>
                Dismiss
              </Button>
            }
            description="Your status could not be updated. Your previous status is unchanged."
            title="Couldn't update application"
          />
        </div>
      )}
      <div className="job-detail-layout">
        <div className="job-detail-primary">
          <Card>
            <CardHeader>
              <CardTitle>About this role</CardTitle>
              <CardDescription>Details from the original job listing.</CardDescription>
            </CardHeader>
            <CardContent>
              {job.description ? (
                <div className="job-detail-description">{job.description}</div>
              ) : (
                <EmptyState
                  description="The source did not provide a job description."
                  title="No description available"
                />
              )}
            </CardContent>
          </Card>
          {match ? (
            <>
              <Card>
                <CardHeader>
                  <CardTitle>What makes you a good match</CardTitle>
                  <CardDescription>
                    Evidence FoxPilot found in your profile and this role.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <MatchReasons match={match} />
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>Potential gaps</CardTitle>
                  <CardDescription>Questions worth considering before you apply.</CardDescription>
                </CardHeader>
                <CardContent>
                  {hasPotentialGaps(match) ? (
                    <MatchGapAnalysis match={match} />
                  ) : (
                    <p className="job-detail-no-gaps">
                      No potential gaps were flagged for this role.
                    </p>
                  )}
                </CardContent>
              </Card>
            </>
          ) : (
            <Card>
              <EmptyState
                description="This role is available, but FoxPilot does not have a match analysis for it yet."
                title="Match analysis unavailable"
              />
            </Card>
          )}
        </div>
        <aside className="job-detail-secondary">
          <MatchPanel match={match} />
          <ApplicationPanel
            application={application}
            jobTitle={job.title}
            updating={updating}
            onStatusChange={(status) => void handleStatus(status)}
          />
        </aside>
      </div>
    </main>
  );
}

function JobHeader({
  job,
  listing,
  match,
  source,
}: {
  job: Job;
  listing?: string;
  match: Match["match"] | null;
  source: string;
}) {
  return (
    <header className="job-detail-header">
      <div className="job-detail-heading">
        <div className="job-detail-company">
          <Avatar initials={job.company.slice(0, 2).toUpperCase()} alt="" />
          <div>
            <span>{job.company}</span>
            <small>{source}</small>
          </div>
        </div>
        <h1>{job.title}</h1>
        <div className="job-detail-meta">
          <span>
            <MapPin size={16} aria-hidden="true" />
            {job.location || "Location not specified"}
          </span>
          {job.last_seen_at && <span>Last seen {formatDate(job.last_seen_at)}</span>}
          {job.is_active === false && (
            <span className="job-detail-inactive">
              This role may no longer be accepting applications.
            </span>
          )}
        </div>
      </div>
      <div className="job-detail-header-actions">
        {match && (
          <div className="job-detail-header-score">
            <MatchScore score={match.match_score} />
            <span>{match.recommendation} recommendation</span>
          </div>
        )}
        {listing && (
          <a
            className="ui-button ui-button-primary ui-button-md"
            href={listing}
            rel="noreferrer"
            target="_blank"
          >
            {job.is_active === false ? "Open original listing" : `Apply on ${source}`}
            <ExternalLink size={16} aria-hidden="true" />
          </a>
        )}
      </div>
    </header>
  );
}

function MatchPanel({ match }: { match: Match["match"] | null }) {
  if (!match)
    return (
      <Card>
        <EmptyState
          icon={<Sparkles size={22} />}
          description="No match evidence is available for this role."
          title="No match summary"
        />
      </Card>
    );
  return (
    <Card variant="selected">
      <CardHeader>
        <CardTitle>Your match</CardTitle>
        <CardDescription>How this opportunity aligns with your profile.</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="job-detail-panel-score">
          <MatchScore score={match.match_score} />
        </div>
        <div className="job-detail-panel-section">
          <strong>Experience match</strong>
          <span>{match.experience_match || "Not specified"}</span>
        </div>
        <div className="job-detail-panel-section">
          <strong>Matching skills</strong>
          <div className="job-detail-skill-list">
            {match.matching_skills.length > 0 ? (
              match.matching_skills.map((skill) => <span key={skill}>{skill}</span>)
            ) : (
              <span className="job-detail-muted">No skills listed</span>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ApplicationPanel({
  application,
  jobTitle,
  onStatusChange,
  updating,
}: {
  application?: Application;
  jobTitle: string;
  onStatusChange: (status: Application["status"]) => void;
  updating: boolean;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Application</CardTitle>
        <CardDescription>Track your decision without leaving FoxPilot.</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="job-detail-application-status">
          <span>Current status</span>
          {application && <strong>{formatStatus(application.status)}</strong>}
        </div>
        <ApplicationStatusSelect
          disabled={updating}
          jobTitle={jobTitle}
          status={application?.status}
          onChange={onStatusChange}
        />
        {updating && (
          <span className="job-detail-status-loading" role="status">
            Updating status...
          </span>
        )}
      </CardContent>
    </Card>
  );
}

function JobDetailSkeleton() {
  return (
    <main className="job-detail-page" aria-label="Loading job details" role="status">
      <Skeleton className="job-detail-skeleton-back" />
      <div className="job-detail-skeleton-header">
        <Skeleton className="job-detail-skeleton-company" />
        <Skeleton className="job-detail-skeleton-title" />
        <Skeleton className="job-detail-skeleton-meta" />
      </div>
      <div className="job-detail-layout">
        <div className="job-detail-primary">
          <Skeleton className="job-detail-skeleton-card" />
          <Skeleton className="job-detail-skeleton-card" />
        </div>
        <div className="job-detail-secondary">
          <Skeleton className="job-detail-skeleton-card" />
          <Skeleton className="job-detail-skeleton-card" />
        </div>
      </div>
    </main>
  );
}

function JobDetailError({ onRetry }: { onRetry: () => void }) {
  return (
    <main className="job-detail-state">
      <ErrorState
        action={
          <>
            <Button type="button" onClick={onRetry}>
              Retry
            </Button>
            <Link className="ui-button ui-button-outline ui-button-md" to="/app/matches">
              Back to Matches
            </Link>
          </>
        }
        description="We couldn't load this opportunity. Please try again."
        title="Unable to load job"
      />
    </main>
  );
}

function JobNotFound() {
  return (
    <main className="job-detail-state">
      <EmptyState
        action={
          <Link className="ui-button ui-button-primary ui-button-md" to="/app/matches">
            Back to Matches
          </Link>
        }
        description="This opportunity may have been removed or is no longer available."
        title="Job not found"
      />
    </main>
  );
}

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function formatStatus(status: Application["status"]) {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function hasPotentialGaps(match: Match["match"]) {
  return (
    match.missing_skills.length > 0 ||
    match.concerns.length > 0 ||
    (match.gap_analysis?.length ?? 0) > 0
  );
}
