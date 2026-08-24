import { ArrowRight, MapPin } from "lucide-react";
import { Link } from "react-router-dom";
import type { Application, Job, Match } from "../../../../api";
import { Badge } from "../../../../shared/ui/Badge";
import { Card } from "../../../../shared/ui/Card";
import { ApplicationStatusSelect } from "../ApplicationStatusSelect";

export function ApplicationCard({
  application,
  job,
  match,
  updating,
  onStatusChange,
}: {
  application: Application;
  job?: Job;
  match?: Match["match"];
  updating: boolean;
  onStatusChange: (status: Application["status"]) => void;
}) {
  const title = application.title ?? job?.title ?? "Untitled role";
  const company = application.company ?? job?.company ?? "Company not specified";
  const statusVariant =
    application.status === "offered"
      ? "success"
      : application.status === "rejected"
        ? "error"
        : application.status === "interviewing"
          ? "brand"
          : "neutral";
  return (
    <Card className="applications-card">
      <div className="applications-card-top">
        <div className="applications-card-copy">
          <span>{company}</span>
          <h3>{title}</h3>
          {job?.location && (
            <p>
              <MapPin size={14} aria-hidden="true" />
              {job.location}
            </p>
          )}
        </div>
        {match && (
          <span className="applications-match-score">
            <strong>{Math.round(match.match_score)}%</strong> match
          </span>
        )}
      </div>
      <div className="applications-card-bottom">
        <Badge variant={statusVariant}>{formatStatus(application.status)}</Badge>
        <div className="applications-card-actions">
          <ApplicationStatusSelect
            disabled={updating}
            jobTitle={title}
            status={application.status}
            onChange={onStatusChange}
          />
          <Link aria-label={`View ${title}`} to={`/app/jobs/${application.job_id}`}>
            <span>View job</span>
            <ArrowRight size={16} aria-hidden="true" />
          </Link>
        </div>
      </div>
    </Card>
  );
}

function formatStatus(status: Application["status"]) {
  return status.charAt(0).toUpperCase() + status.slice(1);
}
