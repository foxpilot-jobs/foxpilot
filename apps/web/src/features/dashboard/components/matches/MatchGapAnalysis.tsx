import { AlertTriangle, HelpCircle, XCircle } from "lucide-react";
import type { Match } from "../../../../api";
import { Badge } from "../../../../shared/ui/Badge";

export function MatchGapAnalysis({ match }: { match: Match["match"] }) {
  const gaps = match.gap_analysis ?? [];
  if (gaps.length === 0 && match.missing_skills.length === 0 && match.concerns.length === 0)
    return null;
  return (
    <details className="matches-gaps" open>
      <summary>Potential gaps and concerns</summary>
      <div className="matches-gap-content">
        {match.missing_skills.length > 0 && (
          <div className="matches-gap-section">
            <strong>Skills to verify</strong>
            <ul className="matches-gap-skills">
              {match.missing_skills.map((skill) => (
                <li key={skill}>{skill}</li>
              ))}
            </ul>
          </div>
        )}
        {gaps.length > 0 && (
          <div className="matches-gap-section">
            <strong>Gap analysis</strong>
            <div className="matches-gap-list">
              {gaps.map((gap, index) => {
                const label = gap.gap || match.missing_skills[index] || "Gap details unavailable";
                const explanation =
                  gap.explanation ||
                  "Review this requirement against your experience before applying.";
                return (
                  <div className="matches-gap-item" key={label || index}>
                    <div className="matches-gap-item-header">
                      <GapIcon severity={gap.severity} />
                      <span className="matches-gap-item-label">{label}</span>
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
                    <p className="matches-gap-item-explanation">{explanation}</p>
                  </div>
                );
              })}
            </div>
          </div>
        )}
        {match.concerns.length > 0 && (
          <div className="matches-gap-section">
            <strong>Concerns</strong>
            <ul className="matches-gap-concerns">
              {match.concerns.map((concern) => (
                <li key={concern}>{concern}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </details>
  );
}

function GapIcon({ severity }: { severity: string }) {
  if (severity === "blocking")
    return <XCircle size={15} className="matches-gap-icon-blocking" aria-hidden="true" />;
  if (severity === "addressable")
    return <AlertTriangle size={15} className="matches-gap-icon-addressable" aria-hidden="true" />;
  return <HelpCircle size={15} className="matches-gap-icon-unknown" aria-hidden="true" />;
}
