import type { Profile } from "../../../api";
import { Badge } from "../../../shared/ui/Badge";
import { Button } from "../../../shared/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "../../../shared/ui/Card";
import { Spinner } from "../../../shared/ui/Spinner";
import { ProfileSection } from "./ProfileSection";

export type ExtractionPhase =
  | "idle"
  | "uploading"
  | "analyzing"
  | "finalizing"
  | "completed_with_fields"
  | "completed_empty"
  | "failed";

export function ProfileOverview({
  extractionPhase = "idle",
  profile,
  onRetryExtraction,
}: {
  extractionPhase?: ExtractionPhase;
  profile: Profile;
  onRetryExtraction?: () => void;
}) {
  const fields = profile.profile;
  const summary = typeof fields.summary === "string" ? fields.summary : null;
  const roles = toStringList(fields.target_roles);
  const skills = unique([
    ...toStringList(fields.skills),
    ...toStringList(fields.programming_languages),
    ...toStringList(fields.data_and_ai_tools),
    ...toStringList(fields.cloud_and_infrastructure),
    ...toStringList(fields.databases),
    ...toStringList(fields.analytics_and_bi_tools),
  ]);
  const experienceList = toStructuredList(fields.current_or_recent_roles ?? fields.experience);
  const sections = [
    { key: "experience", title: "Experience & Roles", values: experienceList },
    { key: "education", title: "Education", values: toStructuredList(fields.education) },
    { key: "projects", title: "Projects", values: toStructuredList(fields.projects) },
    { key: "certifications", title: "Certifications", values: toStringList(fields.certifications) },
    { key: "locations", title: "Locations", values: toStringList(fields.locations) },
    { key: "industries", title: "Industries", values: toStringList(fields.industries) },
  ];
  const hasContent =
    Boolean(summary) ||
    roles.length > 0 ||
    skills.length > 0 ||
    sections.some((section) => section.values.length > 0);

  const isPending =
    extractionPhase === "uploading" ||
    extractionPhase === "analyzing" ||
    extractionPhase === "finalizing";

  return (
    <Card>
      <CardHeader>
        <CardTitle>Extracted profile</CardTitle>
      </CardHeader>
      <CardContent className="profile-overview-content">
        {isPending ? (
          <div
            className="profile-analyzing-state"
            style={{ display: "flex", alignItems: "center", gap: "12px", padding: "16px 0" }}
          >
            <Spinner size={20} />
            <span style={{ color: "var(--color-text-secondary, #666)" }}>
              {extractionPhase === "finalizing"
                ? "Finalizing profile... Syncing extracted fields."
                : "Analyzing your resume... FoxPilot is extracting your skills, experience, education, and target roles."}
            </span>
          </div>
        ) : (
          <>
            {summary && (
              <ProfileSection label="Professional summary" title="About you">
                <p className="profile-summary-text">{summary}</p>
              </ProfileSection>
            )}
            {roles.length > 0 && (
              <ProfileSection label="Direction" title="Target roles">
                <ChipList values={roles} />
              </ProfileSection>
            )}
            {skills.length > 0 && (
              <ProfileSection label="Capabilities" title="Skills and tools">
                <ChipList values={skills} />
              </ProfileSection>
            )}
            {sections.map(
              (section) =>
                section.values.length > 0 && (
                  <ProfileSection key={section.key} title={section.title}>
                    <ul className="profile-structured-list">
                      {section.values.map((value) => (
                        <li key={value}>{value}</li>
                      ))}
                    </ul>
                  </ProfileSection>
                ),
            )}
            {!hasContent && (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "12px",
                  alignItems: "flex-start",
                }}
              >
                <p className="profile-muted">
                  {profile.resume_filename
                    ? "Your profile was extracted, but no structured fields were found. Try re-analyzing or re-uploading a clearer PDF resume."
                    : "No resume uploaded yet. Upload your resume above to extract your career profile."}
                </p>
                {onRetryExtraction && profile.resume_filename && (
                  <Button size="sm" variant="outline" onClick={onRetryExtraction}>
                    Re-analyze resume
                  </Button>
                )}
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function ChipList({ values }: { values: string[] }) {
  return (
    <div className="profile-chip-list">
      {values.map((value) => (
        <Badge key={value} variant="info">
          {value}
        </Badge>
      ))}
    </div>
  );
}
function toStringList(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}
function toStructuredList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    if (typeof item === "string") return [item];
    if (!item || typeof item !== "object") return [];
    const record = item as Record<string, unknown>;
    const primary = ["title", "role", "position", "name", "school", "institution"].find(
      (key) => typeof record[key] === "string",
    );
    const secondary = ["company", "organization", "degree"].find(
      (key) => typeof record[key] === "string",
    );
    if (!primary) return [];
    return [secondary ? `${record[primary]} · ${record[secondary]}` : String(record[primary])];
  });
}
function unique(values: string[]) {
  return [...new Set(values)];
}
