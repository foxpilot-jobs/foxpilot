import type { Profile } from "../../../api";
import { Badge } from "../../../shared/ui/Badge";
import { Card, CardContent, CardHeader, CardTitle } from "../../../shared/ui/Card";
import { ProfileSection } from "./ProfileSection";

export function ProfileOverview({ profile }: { profile: Profile }) {
  const fields = profile.profile;
  const summary = typeof fields.summary === "string" ? fields.summary : null;
  const roles = toStringList(fields.target_roles);
  const skills = unique([
    ...toStringList(fields.skills),
    ...toStringList(fields.programming_languages),
    ...toStringList(fields.data_and_ai_tools),
  ]);
  const sections = [
    { key: "experience", title: "Experience", values: toStructuredList(fields.experience) },
    { key: "education", title: "Education", values: toStructuredList(fields.education) },
    { key: "locations", title: "Locations", values: toStringList(fields.locations) },
    { key: "industries", title: "Industries", values: toStringList(fields.industries) },
  ];
  return (
    <Card>
      <CardHeader>
        <CardTitle>Extracted profile</CardTitle>
      </CardHeader>
      <CardContent className="profile-overview-content">
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
        {!summary &&
          roles.length === 0 &&
          skills.length === 0 &&
          sections.every((section) => section.values.length === 0) && (
            <p className="profile-muted">
              Your profile was extracted, but no structured fields are available to display yet.
            </p>
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
