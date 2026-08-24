import type { CSSProperties } from "react";
import { Badge } from "../../../../shared/ui/Badge";

export function MatchScore({ score }: { score: number }) {
  const label =
    score >= 90
      ? "Strong match"
      : score >= 75
        ? "Good match"
        : score >= 60
          ? "Moderate match"
          : "Lower match";
  const variant = score >= 75 ? "success" : score >= 60 ? "warning" : "neutral";
  const clamped = Math.max(0, Math.min(100, score));
  return (
    <span className="matches-score">
      <span className="matches-score-figure">
        <strong>{Math.round(score)}%</strong>
        <span
          aria-hidden="true"
          className="matches-score-bar"
          style={{ "--score-pct": `${clamped}%` } as CSSProperties}
        >
          <span className="matches-score-bar-fill" />
        </span>
      </span>
      <Badge variant={variant}>{label}</Badge>
    </span>
  );
}
