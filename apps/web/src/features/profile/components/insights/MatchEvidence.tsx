import { ArrowRight, MapPin } from "lucide-react";
import { Link } from "react-router-dom";
import type { Match } from "../../../../api";
import { Badge } from "../../../../shared/ui/Badge";
import { Card, CardContent, CardHeader, CardTitle } from "../../../../shared/ui/Card";

export function MatchEvidence({ matches }: { matches: Match[] }) {
  const examples = [...matches]
    .sort((left, right) => right.match.match_score - left.match.match_score)
    .slice(0, 3);
  if (examples.length === 0) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Match examples</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="insights-example-list">
          {examples.map((item) => (
            <article className="insights-example" key={item.job_id}>
              <div>
                <span>{item.job.company}</span>
                <h3>{item.job.title}</h3>
                <p>
                  <MapPin size={14} aria-hidden="true" />
                  {item.job.location || "Location not specified"}
                </p>
              </div>
              <div className="insights-example-side">
                <strong>{Math.round(item.match.match_score)}%</strong>
                <Badge
                  variant={
                    item.match.recommendation === "APPLY"
                      ? "success"
                      : item.match.recommendation === "CONSIDER"
                        ? "warning"
                        : "neutral"
                  }
                >
                  {item.match.recommendation}
                </Badge>
                <Link aria-label={`View ${item.job.title}`} to={`/app/jobs/${item.job_id}`}>
                  <ArrowRight size={17} aria-hidden="true" />
                </Link>
              </div>
            </article>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
