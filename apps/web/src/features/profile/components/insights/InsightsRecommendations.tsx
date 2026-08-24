import { ArrowRight, Lightbulb } from "lucide-react";
import { Link } from "react-router-dom";
import type { RecommendationInsight } from "../../insights/deriveInsights";
import { Card, CardContent, CardHeader, CardTitle } from "../../../../shared/ui/Card";

export function InsightsRecommendations({
  recommendations,
}: {
  recommendations: RecommendationInsight[];
}) {
  if (recommendations.length === 0) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recommendations</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="insights-recommendations">
          {recommendations.map((recommendation) => (
            <article key={recommendation.title}>
              <Lightbulb size={18} aria-hidden="true" />
              <div>
                <h3>{recommendation.title}</h3>
                <p>{recommendation.explanation}</p>
              </div>
            </article>
          ))}
        </div>
        <Link className="insights-inline-link" to="/app/matches">
          Explore opportunities
          <ArrowRight size={16} aria-hidden="true" />
        </Link>
      </CardContent>
    </Card>
  );
}
