import { CheckCircle2 } from "lucide-react";
import type { StrengthInsight } from "../../insights/deriveInsights";
import { Card, CardContent, CardHeader, CardTitle } from "../../../../shared/ui/Card";
import { EmptyState } from "../../../../shared/ui/EmptyState";

export function StrengthsSection({ strengths }: { strengths: StrengthInsight[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Your strengths</CardTitle>
      </CardHeader>
      <CardContent>
        {strengths.length === 0 ? (
          <EmptyState
            description="As FoxPilot evaluates more opportunities, recurring strengths will appear here."
            title="Not enough evidence yet"
          />
        ) : (
          <div className="insights-strength-list">
            {strengths.map((strength) => (
              <article className="insights-strength" key={strength.title}>
                <CheckCircle2 size={19} aria-hidden="true" />
                <div>
                  <h3>{strength.title}</h3>
                  <p>{strength.explanation}</p>
                  <small>{strength.evidence}</small>
                </div>
              </article>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
