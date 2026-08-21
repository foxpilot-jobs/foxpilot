import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  getBackgroundJob,
  getProfile,
  runScan,
  runMatching,
  uploadResume,
  type BackgroundJob,
  type Profile,
} from "../../../api";
import { Alert } from "../../../shared/components/Alert";
import { Button } from "../../../shared/components/Button";
import { LoadingState } from "../../../shared/components/LoadingState";

export function ProfileSetupPage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [activeJob, setActiveJob] = useState<BackgroundJob | null>(null);

  useEffect(() => {
    getProfile()
      .then(setProfile)
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : "Unable to load profile"),
      )
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const jobId = activeJob?.job_id;
    if (!jobId) return;
    let stopped = false;
    let timer: number | undefined;
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
          setError(job.error ?? "The background job failed");
          return;
        }
        timer = window.setTimeout(() => void poll(), job.kind === "matching" ? 5000 : 3000);
      } catch (reason: unknown) {
        if (!stopped)
          setError(reason instanceof Error ? reason.message : "Unable to check job status");
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
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      setActiveJob(await uploadResume(file));
      setMessage("Resume received. FoxPilot is extracting your profile in the background.");
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to process resume");
    } finally {
      setBusy(false);
    }
  }

  async function handleMatching() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      setActiveJob(await runMatching());
      setMessage(
        "Matching started. FoxPilot is comparing your profile with the current shortlist.",
      );
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to run matching");
    } finally {
      setBusy(false);
    }
  }

  async function handleScan() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      setActiveJob(await runScan());
      setMessage("Scan started. FoxPilot is searching for roles derived from your profile.");
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to scan for jobs");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <LoadingState label="Loading your profile..." />;

  const fields = profile?.profile ?? {};
  const skills = [
    ...toStringList(fields.skills),
    ...toStringList(fields.programming_languages),
    ...toStringList(fields.data_and_ai_tools),
  ];
  const roles = toStringList(fields.target_roles);
  const processing = busy || activeJob?.status === "queued" || activeJob?.status === "running";

  return (
    <main className="profile-shell">
      <div className="profile-header">
        <p className="eyebrow accent">YOUR PROFILE</p>
        <h1>Give FoxPilot the context to find your strongest next move.</h1>
        <p className="hero-copy">
          Upload a PDF resume. FoxPilot extracts a private working profile, then compares it against
          the jobs you choose to review.
        </p>
      </div>
      {error && <Alert>{error}</Alert>}
      {message && <Alert tone="success">{message}</Alert>}
      <section className="profile-upload-card">
        <label className="upload-dropzone">
          <span className="upload-title">
            {processing
              ? "FoxPilot is working..."
              : profile
                ? "Replace your resume"
                : "Upload your resume"}
          </span>
          <span className="upload-help">
            PDF only, up to 10 MB. Your resume stays associated with your account.
          </span>
          <input
            accept="application/pdf,.pdf"
            disabled={processing}
            type="file"
            onChange={(event) => void handleUpload(event.target.files?.[0])}
          />
        </label>
        <AsyncStatus job={activeJob} />
        {profile && (
          <div className="profile-summary">
            <div className="card-topline">
              <strong>{profile.resume_filename}</strong>
              <span className="count-pill">Profile ready</span>
            </div>
            <p>{String(fields.summary ?? "Structured profile extracted from your resume.")}</p>
            {roles.length > 0 && <ProfileList label="Target roles" values={roles} />}
            {skills.length > 0 && (
              <ProfileList label="Skills and tools" values={[...new Set(skills)]} />
            )}
            {activeJob?.kind === "matching" && activeJob.status === "completed" && (
              <Link className="match-link" to="/app">
                View your matches
              </Link>
            )}
            <Button disabled={processing} onClick={() => void handleScan()}>
              Scan profile-specific jobs
            </Button>
            <Button disabled={processing} onClick={() => void handleMatching()}>
              Run matching
            </Button>
          </div>
        )}
      </section>
    </main>
  );
}

function AsyncStatus({ job }: { job: BackgroundJob | null }) {
  if (!job || job.status === "completed") return null;
  if (job.status === "failed") {
    return (
      <div className="async-status async-status-error">Processing failed. You can try again.</div>
    );
  }
  const progress = job.result as { processed?: number; total?: number } | null;
  const progressLabel =
    job.kind === "matching" && progress?.total
      ? `Comparing roles against your profile... ${progress.processed ?? 0}/${progress.total}`
      : job.kind === "profile_generation"
        ? "Reading your experience and skills..."
        : job.kind === "scan"
          ? "Searching sources for profile-specific roles..."
          : "Comparing roles against your profile...";
  return (
    <div className="async-status">
      <span className="loading-spinner" aria-hidden="true" />
      {progressLabel}
    </div>
  );
}

function toStringList(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

function ProfileList({ label, values }: { label: string; values: string[] }) {
  return (
    <div className="profile-list">
      <strong>{label}</strong>
      <div className="tag-list">
        {values.map((value) => (
          <span className="tag" key={value}>
            {value}
          </span>
        ))}
      </div>
    </div>
  );
}
