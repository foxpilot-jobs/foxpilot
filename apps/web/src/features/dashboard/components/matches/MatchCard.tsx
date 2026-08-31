import { ExternalLink, MapPin } from "lucide-react";
import { Link } from "react-router-dom";
import { availableJobSources, type Application, type Match } from "../../../../api";
import { Avatar } from "../../../../shared/ui/Avatar";
import { Badge } from "../../../../shared/ui/Badge";
import { ApplicationStatusSelect } from "../ApplicationStatusSelect";
import { MatchGapAnalysis } from "./MatchGapAnalysis";
import { MatchReasons } from "./MatchReasons";
import { MatchScore } from "./MatchScore";

export function MatchCard({
  application,
  item,
  onStatusChange,
  updating,
}: {
  application?: Application;
  item: Match;
  onStatusChange: (status: Application["status"]) => void;
  updating: boolean;
}) {
  const { job, match } = item;
  const recommendationVariant =
    match.recommendation === "APPLY"
      ? "success"
      : match.recommendation === "CONSIDER"
        ? "warning"
        : "neutral";
  const availableSources = availableJobSources(job);
  const source = availableSources[0]?.source ?? job.source;
  return (
    <article className="matches-card">
      <header className="matches-card-header">
        <div className="matches-company">
          <Avatar initials={job.company.slice(0, 2).toUpperCase()} alt="" />
          <div>
            <span>{job.company}</span>
            <p>{source ?? "Job source"}</p>
          </div>
        </div>
        <div className="matches-card-score">
          <MatchScore score={match.match_score} />
          <Badge variant={recommendationVariant}>{match.recommendation}</Badge>
        </div>
      </header>
      <div className="matches-card-title">
        <h2>{job.title}</h2>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            flexWrap: "wrap",
            marginTop: "0.25rem",
          }}
        >
          <p style={{ margin: 0, display: "flex", alignItems: "center", gap: "0.25rem" }}>
            <MapPin size={15} aria-hidden="true" />
            {job.location || "Location not specified"}
          </p>
          {job.work_arrangement?.display_label && (
            <Badge variant={job.work_arrangement.is_india_eligible === false ? "warning" : "info"}>
              {job.work_arrangement.display_label}
            </Badge>
          )}
        </div>
      </div>
      <MatchReasons match={match} />
      <div className="matches-skills">
        <strong>Skills you match</strong>
        <div>
          {match.matching_skills.length > 0 ? (
            match.matching_skills.map((skill) => (
              <Badge key={skill} variant="info">
                {skill}
              </Badge>
            ))
          ) : (
            <span className="matches-muted">No matching skills listed</span>
          )}
        </div>
      </div>
      <MatchGapAnalysis match={match} />
      <footer className="matches-card-footer">
        <div className="matches-card-actions">
          <Link className="matches-primary-link" to={`/app/jobs/${item.job_id}`}>
            View details
          </Link>
          {availableSources.length > 0 ? (
            <a href={availableSources[0].url} rel="noreferrer" target="_blank">
              Open original listing <ExternalLink size={14} aria-hidden="true" />
            </a>
          ) : (
            job.url && (
              <a href={job.url} rel="noreferrer" target="_blank">
                Open original listing <ExternalLink size={14} aria-hidden="true" />
              </a>
            )
          )}
        </div>
        <ApplicationStatusSelect
          disabled={updating}
          jobTitle={job.title}
          status={application?.status}
          onChange={onStatusChange}
        />
      </footer>
    </article>
  );
}
