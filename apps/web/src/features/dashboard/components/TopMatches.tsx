import { ArrowRight, MapPin } from "lucide-react";
import { Link } from "react-router-dom";
import type { Match } from "../../../api";
import { Badge } from "../../../shared/ui/Badge";
import { EmptyState } from "../../../shared/ui/EmptyState";

export function TopMatches({ matches }: { matches: Match[] }) {
  const topMatches = [...matches]
    .sort((left, right) => right.match.match_score - left.match.match_score)
    .slice(0, 5);
  return (
    <section className="dashboard-panel" aria-labelledby="top-matches-heading">
      <div className="dashboard-section-heading">
        <div>
          <p className="ui-eyebrow">Personalized discovery</p>
          <h2 id="top-matches-heading">Top matches for you</h2>
        </div>
        <Link className="dashboard-view-all" to="/app/matches">
          View all <ArrowRight size={16} aria-hidden="true" />
        </Link>
      </div>
      {topMatches.length === 0 ? (
        <EmptyState
          description="Complete your profile and run matching to see roles selected for your experience."
          title="No matches yet"
        />
      ) : (
        <div className="dashboard-match-list">
          {topMatches.map((item) => (
            <TopMatchRow item={item} key={item.job_id} />
          ))}
        </div>
      )}
    </section>
  );
}

function TopMatchRow({ item }: { item: Match }) {
  const { job, match } = item;
  const scoreVariant =
    match.match_score >= 70 ? "success" : match.match_score >= 40 ? "warning" : "neutral";
  return (
    <article className="dashboard-match-row">
      <div className="dashboard-match-main">
        <span className="dashboard-match-company">{job.company}</span>
        <h3>{job.title}</h3>
        <span className="dashboard-match-location">
          <MapPin size={14} aria-hidden="true" />
          {job.location || "Location not specified"}
        </span>
      </div>
      <div className="dashboard-match-evidence">
        <Badge variant={scoreVariant}>{Math.round(match.match_score)}% fit</Badge>
        <Badge variant="brand">{match.recommendation}</Badge>
        <span>
          {match.matching_skills.slice(0, 2).join(" · ") ||
            match.reasons[0] ||
            "Profile alignment identified"}
        </span>
      </div>
      <Link
        aria-label={`View evaluation for ${job.title} at ${job.company}`}
        className="dashboard-match-link"
        to={`/app/jobs/${item.job_id}`}
      >
        <ArrowRight size={18} aria-hidden="true" />
      </Link>
    </article>
  );
}
