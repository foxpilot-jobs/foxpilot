import { Check } from "lucide-react";
import type { Match } from "../../../../api";

export function MatchReasons({ match }: { match: Match["match"] }) {
  const reasons = match.reasons.slice(0, 3);
  if (reasons.length === 0 && !match.experience_match) return null;
  return (
    <details className="matches-reasons" open>
      <summary>Why FoxPilot recommends this</summary>
      <ul>
        {reasons.map((reason) => (
          <li key={reason}>
            <Check size={15} aria-hidden="true" />
            <span>{reason}</span>
          </li>
        ))}
        {reasons.length === 0 && (
          <li>
            <Check size={15} aria-hidden="true" />
            <span>{match.experience_match}</span>
          </li>
        )}
      </ul>
    </details>
  );
}
