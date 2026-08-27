import { useEffect, useState } from "react";
import {
  getBackgroundJob,
  getProfile,
  runMatching,
  uploadResume,
  type BackgroundJob,
  type Profile,
} from "../../../api";
import { Alert } from "../../../shared/ui/Alert";
import { ErrorState } from "../../../shared/ui/ErrorState";
import { Spinner } from "../../../shared/ui/Spinner";
import { Toast } from "../../../shared/ui/Toast";
import { ProfileActions } from "../components/ProfileActions";
import { ProfileHeader } from "../components/ProfileHeader";
import { ProfileInsightsLink } from "../components/ProfileInsightsLink";
import { ProfileOverview } from "../components/ProfileOverview";
import { ProfileReadiness } from "../components/ProfileReadiness";
import { ProfileSkeleton } from "../components/ProfileSkeleton";
import { ResumeCard } from "../components/ResumeCard";

const JOB_POLL_DELAYS_MS = [3000, 6000, 12000, 24000, 30000, 30000, 30000, 30000, 30000];

export function ProfileSetupPage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [activeAction, setActiveAction] = useState<"upload" | "matching" | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [activeJob, setActiveJob] = useState<BackgroundJob | null>(null);
  const [selectedFileName, setSelectedFileName] = useState<string | undefined>();
  const [retryToken, setRetryToken] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setLoadError(false);
    void getProfile()
      .then((loadedProfile) => {
        if (active) setProfile(loadedProfile);
      })
      .catch(() => {
        if (active) setLoadError(true);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [retryToken]);

  useEffect(() => {
    const jobId = activeJob?.job_id;
    if (!jobId) return;
    let stopped = false;
    let timer: number | undefined;
    let pollCount = 0;
    const startedAt = Date.now();
    const poll = async () => {
      try {
        const job = await getBackgroundJob(jobId);
        if (stopped) return;
        setActiveJob(job);
        if (job.status === "completed" && job.kind === "profile_generation") {
          const loadedProfile = await getProfile();
          if (!stopped) {
            setProfile(loadedProfile);
            setMessage("Profile extracted. Review the fields below, then run matching when ready.");
          }
          return;
        }
        if (job.status === "completed" && job.kind === "matching") {
          const result = job.result as {
            analyzed?: number;
            skipped?: number;
            failed?: number;
          } | null;
          setMessage(
            `Matching complete: ${result?.analyzed ?? 0} analyzed, ${result?.skipped ?? 0} already current, ${result?.failed ?? 0} failed.`,
          );
          return;
        }
        if (job.status === "completed" && job.kind === "scan") {
          const result = job.result as { new_jobs?: number } | null;
          setMessage(
            `Scan complete: ${result?.new_jobs ?? 0} new jobs discovered. Run matching when ready.`,
          );
          return;
        }
        if (job.status === "failed") {
          setActionError("We couldn't process this background job. You can try again.");
          return;
        }
        const delay = JOB_POLL_DELAYS_MS[pollCount] ?? JOB_POLL_DELAYS_MS.at(-1)!;
        pollCount += 1;
        if (Date.now() - startedAt + delay > 5 * 60 * 1000) {
          setActiveJob(null);
          setActionError("Processing is taking longer than expected. Please try again shortly.");
          return;
        }
        timer = window.setTimeout(() => void poll(), delay);
      } catch {
        if (!stopped) setActionError("We couldn't check the background job. Please try again.");
      }
    };
    void poll();
    return () => {
      stopped = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [activeJob?.job_id]);

  async function handleUpload(file: File | undefined) {
    if (!file) return;
    setSelectedFileName(file.name);
    setBusy(true);
    setActiveAction("upload");
    setActionError(null);
    setMessage(null);
    try {
      setActiveJob(await uploadResume(file));
      setMessage("Resume received. FoxPilot is extracting your profile in the background.");
    } catch {
      setActionError("We couldn't upload your resume. Please check that it is a PDF under 10 MB.");
    } finally {
      setBusy(false);
      setActiveAction(null);
    }
  }

  async function handleMatching() {
    setBusy(true);
    setActiveAction("matching");
    setActionError(null);
    setMessage(null);
    try {
      setActiveJob(await runMatching());
      setMessage(
        "Matching started. FoxPilot is comparing your profile with the current shortlist.",
      );
    } catch {
      setActionError("We couldn't start matching. Please try again.");
    } finally {
      setBusy(false);
      setActiveAction(null);
    }
  }

  if (loading) return <ProfileSkeleton />;
  if (loadError)
    return (
      <main className="profile-state">
        <ErrorState
          action={
            <button
              className="ui-button ui-button-primary ui-button-md"
              type="button"
              onClick={() => setRetryToken((token) => token + 1)}
            >
              Try again
            </button>
          }
          description="We couldn't load your profile. Please try again."
          title="Unable to load profile"
        />
      </main>
    );

  const fields = profile?.profile ?? {};
  const hasProfileData = Boolean(profile && Object.keys(fields).length > 0);
  const jobProcessing = activeJob?.status === "queued" || activeJob?.status === "running";
  const processing = busy || jobProcessing;
  const resumeBusy =
    activeAction === "upload" || (jobProcessing && activeJob?.kind === "profile_generation");
  return (
    <main className="profile-page">
      <ProfileHeader hasProfileData={hasProfileData} profile={profile} />
      {message && (
        <div className="profile-message">
          <Toast title="Profile update" variant="success" onDismiss={() => setMessage(null)}>
            {message}
          </Toast>
        </div>
      )}
      {actionError && (
        <div className="profile-action-error">
          <Alert variant="error">{actionError}</Alert>
        </div>
      )}
      <ProfileReadiness hasProfileData={hasProfileData} profile={profile} />
      <div className="profile-page-layout">
        <div className="profile-page-primary">
          <ResumeCard
            busy={resumeBusy}
            onFile={handleUpload}
            profile={profile}
            selectedFileName={selectedFileName}
          />
          {profile && <ProfileOverview profile={profile} />}
        </div>
        <aside className="profile-page-secondary">
          {activeJob && <ProfileJobStatus job={activeJob} />}
          {profile && (
            <ProfileActions
              disabled={processing}
              onMatching={() => void handleMatching()}
              loading={
                activeAction === "matching" || (jobProcessing && activeJob?.kind === "matching")
              }
            />
          )}
          <ProfileInsightsLink />
        </aside>
      </div>
    </main>
  );
}

function ProfileJobStatus({ job }: { job: BackgroundJob }) {
  if (job.status === "completed")
    return (
      <div className="profile-job-status profile-job-complete" role="status">
        <strong>Profile workflow complete</strong>
        <span>FoxPilot has finished the latest {formatJobKind(job.kind)}.</span>
      </div>
    );
  if (job.status === "failed")
    return (
      <div className="profile-job-status profile-job-failed" role="alert">
        <strong>We couldn't complete this {formatJobKind(job.kind)}</strong>
        <span>Nothing was changed. You can try the action again when ready.</span>
      </div>
    );
  return (
    <div className="profile-job-status" role="status" aria-live="polite">
      <Spinner size={18} />
      <div>
        <strong>{job.status === "queued" ? "Queued" : "Running"}</strong>
        <span>
          {job.kind === "profile_generation"
            ? "FoxPilot is extracting your experience, skills, and career profile."
            : job.kind === "scan"
              ? "FoxPilot is searching for profile-specific roles."
              : "FoxPilot is comparing roles against your profile."}
        </span>
      </div>
    </div>
  );
}

function formatJobKind(kind: BackgroundJob["kind"]) {
  return kind === "profile_generation"
    ? "resume analysis"
    : kind === "scan"
      ? "job scan"
      : "matching run";
}
