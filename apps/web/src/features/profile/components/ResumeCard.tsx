import { FileText, RefreshCw, Trash2 } from "lucide-react";
import type { Profile } from "../../../api";
import { Badge } from "../../../shared/ui/Badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../../shared/ui/Card";
import { ResumeUpload } from "./ResumeUpload";

export function ResumeCard({
  busy,
  onFile,
  onDeleteResume,
  onRetryExtraction,
  profile,
  selectedFileName,
}: {
  busy: boolean;
  onFile: (file: File | undefined) => void;
  onDeleteResume?: () => void;
  onRetryExtraction?: () => void;
  profile: Profile | null;
  selectedFileName?: string;
}) {
  return (
    <Card id="resume">
      <CardHeader>
        <div>
          <CardTitle>Resume</CardTitle>
          <CardDescription>
            Your resume is the starting point for your personalized profile.
          </CardDescription>
        </div>
        {profile && <FileText size={20} aria-hidden="true" />}
      </CardHeader>
      <CardContent>
        {profile?.resume_filename && (
          <div className="profile-resume-current">
            <span className="profile-resume-file-icon">
              <FileText size={18} aria-hidden="true" />
            </span>
            <div>
              <strong>{profile.resume_filename}</strong>
              <span>Updated {formatDate(profile.updated_at)}</span>
            </div>
            {busy ? (
              <Badge variant="warning">Analyzing resume…</Badge>
            ) : (
              <Badge variant="success">Uploaded</Badge>
            )}
            {!busy && onRetryExtraction && (
              <button
                aria-label="Re-analyze resume"
                className="profile-resume-delete"
                title="Re-analyze resume"
                type="button"
                onClick={onRetryExtraction}
              >
                <RefreshCw size={15} aria-hidden="true" />
              </button>
            )}
            {onDeleteResume && (
              <button
                aria-label="Remove resume"
                className="profile-resume-delete"
                title="Remove resume"
                type="button"
                onClick={onDeleteResume}
              >
                <Trash2 size={15} aria-hidden="true" />
              </button>
            )}
          </div>
        )}
        <ResumeUpload disabled={busy} onFile={onFile} selectedFileName={selectedFileName} />
      </CardContent>
    </Card>
  );
}

function formatDate(value: string | null) {
  if (!value) return "Recently";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}
