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
  return (
    <span className="matches-score">
      <strong>{Math.round(score)}%</strong>
      <Badge variant={variant}>{label}</Badge>
    </span>
  );
}
