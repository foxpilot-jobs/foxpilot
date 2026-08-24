import { Target, UserRound } from "lucide-react";
import type { ProfileSnapshot } from "../../insights/deriveInsights";
import { Badge } from "../../../../shared/ui/Badge";
import { Card, CardContent, CardHeader, CardTitle } from "../../../../shared/ui/Card";

export function CareerSnapshot({ snapshot }: { snapshot: ProfileSnapshot }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Career snapshot</CardTitle>
      </CardHeader>
      <CardContent className="insights-snapshot-content">
        <div className="insights-snapshot-intro">
          <span className="insights-icon">
            <UserRound size={19} aria-hidden="true" />
          </span>
          <p>Here&apos;s how FoxPilot currently understands you.</p>
        </div>
        {snapshot.summary && <p className="insights-summary">{snapshot.summary}</p>}
        {snapshot.targetRoles.length > 0 && (
          <div className="insights-data-group">
            <div className="insights-data-label">
              <Target size={15} aria-hidden="true" />
              Target roles
            </div>
            <div className="insights-chip-list">
              {snapshot.targetRoles.map((role) => (
                <Badge key={role} variant="brand">
                  {role}
                </Badge>
              ))}
            </div>
          </div>
        )}
        {snapshot.skills.length > 0 && (
          <div className="insights-data-group">
            <div className="insights-data-label">Core skills and tools</div>
            <div className="insights-chip-list">
              {snapshot.skills.map((skill) => (
                <Badge key={skill} variant="info">
                  {skill}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
