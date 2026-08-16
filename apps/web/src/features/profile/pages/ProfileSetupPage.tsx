import { useEffect, useState } from "react";
import { getProfile, runMatching, uploadResume, type Profile } from "../../../api";
import { Alert } from "../../../shared/components/Alert";
import { Button } from "../../../shared/components/Button";
import { LoadingState } from "../../../shared/components/LoadingState";

export function ProfileSetupPage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    getProfile()
      .then(setProfile)
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : "Unable to load profile"),
      )
      .finally(() => setLoading(false));
  }, []);

  async function handleUpload(file: File | undefined) {
    if (!file) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      setProfile(await uploadResume(file));
      setMessage("Profile extracted. Review the fields below, then run matching when ready.");
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
      const result = await runMatching();
      setMessage(
        `Matching complete: ${result.analyzed} analyzed, ${result.skipped} already current, ${result.failed} failed.`,
      );
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to run matching");
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
            {busy
              ? "Processing your resume..."
              : profile
                ? "Replace your resume"
                : "Upload your resume"}
          </span>
          <span className="upload-help">
            PDF only, up to 10 MB. Your resume stays associated with your account.
          </span>
          <input
            accept="application/pdf,.pdf"
            disabled={busy}
            type="file"
            onChange={(event) => void handleUpload(event.target.files?.[0])}
          />
        </label>
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
            <Button disabled={busy} onClick={() => void handleMatching()}>
              Run matching
            </Button>
          </div>
        )}
      </section>
    </main>
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
