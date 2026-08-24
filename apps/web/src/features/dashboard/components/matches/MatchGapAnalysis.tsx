import type { Match } from "../../../../api";
import { Badge } from "../../../../shared/ui/Badge";

export function MatchGapAnalysis({ match }: { match: Match["match"] }) {
  const gaps = match.gap_analysis ?? [];
  if (gaps.length === 0 && match.missing_skills.length === 0 && match.concerns.length === 0)
    return null;
  return (
    <details className="matches-gaps">
      <summary>Potential gaps and concerns</summary>
      <div className="matches-gap-content">
        {match.missing_skills.length > 0 && (
          <div>
            <strong>Skills to verify</strong>
            <p>{match.missing_skills.join(", ")}</p>
          </div>
        )}
        {gaps.map((gap) => (
          <div className="matches-gap-item" key={`${gap.gap}-${gap.severity}`}>
            <div>
              <strong>{gap.gap}</strong>
              <Badge
                variant={
                  gap.severity === "blocking"
                    ? "error"
                    : gap.severity === "addressable"
                      ? "warning"
                      : "neutral"
                }
              >
                {gap.severity}
              </Badge>
            </div>
            <p>{gap.explanation}</p>
          </div>
        ))}
        {match.concerns.length > 0 && (
          <div>
            <strong>Concerns</strong>
            <p>{match.concerns.join(", ")}</p>
          </div>
        )}
      </div>
    </details>
  );
}
