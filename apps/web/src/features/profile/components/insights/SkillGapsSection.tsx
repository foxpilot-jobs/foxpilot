import { AlertTriangle } from "lucide-react";
import type { GapInsight } from "../../insights/deriveInsights";
import { Badge } from "../../../../shared/ui/Badge";
import { Card, CardContent, CardHeader, CardTitle } from "../../../../shared/ui/Card";

export function SkillGapsSection({
  gaps,
  matchesAvailable,
}: {
  gaps: GapInsight[];
  matchesAvailable: boolean;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Skill gaps</CardTitle>
      </CardHeader>
      <CardContent>
        {!matchesAvailable ? (
          <p className="insights-muted">
            Match-based gap analysis will appear when your matching data is available.
          </p>
        ) : gaps.length === 0 ? (
          <p className="insights-muted">
            Your current matches don&apos;t show any recurring skill gaps.
          </p>
        ) : (
          <div className="insights-gap-list">
            {gaps.map((gap) => (
              <article className="insights-gap" key={`${gap.gap}-${gap.severity}`}>
                <AlertTriangle size={17} aria-hidden="true" />
                <div>
                  <div className="insights-gap-title">
                    <h3>{gap.gap}</h3>
                    <Badge
                      variant={
                        gap.severity === "addressable"
                          ? "warning"
                          : gap.severity === "blocking"
                            ? "error"
                            : "neutral"
                      }
                    >
                      {gap.severity}
                    </Badge>
                  </div>
                  <p>{gap.explanation}</p>
                  <small>
                    Appears in {gap.occurrences}{" "}
                    {gap.occurrences === 1 ? "opportunity" : "opportunities"}
                  </small>
                </div>
              </article>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
