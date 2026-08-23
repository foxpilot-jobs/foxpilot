import type { Application, Job, Match } from "../../../api";
import { ApplicationStatusSelect } from "./ApplicationStatusSelect";

type JobCardProps = {
  job: Job;
  match?: Match["match"];
  application?: Application;
  updating: boolean;
  onStatusChange: (status: Application["status"]) => void;
};

export function JobCard({ application, job, match, onStatusChange, updating }: JobCardProps) {
  const scoreTone =
    match && match.match_score >= 70
      ? "strong"
      : match && match.match_score >= 40
        ? "possible"
        : "weak";
  return (
    <article className="job-card">
      <div className="card-topline">
        <span className="source-label">
          {job.sources?.map((source) => source.source).join(" + ") || job.source || "JOB SOURCE"}
        </span>
        {job.is_active === false && <span className="count-pill">Closed</span>}
        {match && <span className={`score score-${scoreTone}`}>{match.match_score}% fit</span>}
      </div>
      <h3>{job.title}</h3>
      <p className="company">{job.company}</p>
      <p className="location">{job.location || "Location not specified"}</p>
      {match && (
        <span className={`recommendation recommendation-${match.recommendation.toLowerCase()}`}>
          {match.recommendation}
        </span>
      )}
      {match && <p className="reason">{match.reasons[0] ?? match.experience_match}</p>}
      {match && (
        <details className="evidence">
          <summary>Why this match</summary>
          <div className="evidence-grid">
            <div>
              <strong>Strengths</strong>
              <span>{match.matching_skills.join(", ") || "Profile alignment identified"}</span>
            </div>
            <div>
              <strong>Gaps to verify</strong>
              <span>{match.missing_skills.join(", ") || "No major gaps found"}</span>
            </div>
            {match.gap_analysis && match.gap_analysis.length > 0 && (
              <div>
                <strong>Addressability</strong>
                <span>
                  {match.gap_analysis
                    .map((gap) => `${gap.gap}: ${gap.severity}. ${gap.explanation}`)
                    .join(" ")}
                </span>
              </div>
            )}
            <div>
              <strong>Concerns</strong>
              <span>{match.concerns.join(", ") || "None flagged"}</span>
            </div>
          </div>
        </details>
      )}
      <div className="card-actions">
        {job.sources && job.sources.length > 0
          ? job.sources.map((source) => (
              <a
                href={source.url}
                key={`${source.source}-${source.source_job_id}`}
                rel="noreferrer"
                target="_blank"
              >
                View on {source.source}
              </a>
            ))
          : job.url && (
              <a href={job.url} target="_blank" rel="noreferrer">
                View role
              </a>
            )}
        <ApplicationStatusSelect
          disabled={updating}
          jobTitle={job.title}
          status={application?.status}
          onChange={onStatusChange}
        />
      </div>
    </article>
  );
}
