import type { MatchPattern } from "../../insights/deriveInsights";
import { Card, CardContent, CardHeader, CardTitle } from "../../../../shared/ui/Card";

export function MatchPatterns({ patterns }: { patterns: MatchPattern[] }) {
  if (patterns.length === 0) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Match patterns</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="insights-pattern-grid">
          {patterns.map((pattern) => (
            <div className="insights-pattern" key={pattern.label}>
              <span>{pattern.label}</span>
              <strong>{pattern.value}</strong>
              <small>{pattern.detail}</small>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
