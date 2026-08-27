import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import type { Application, Job } from "../../../api";
import { EmptyState } from "../../../shared/ui/EmptyState";
import { ApplicationStatusSelect } from "./ApplicationStatusSelect";

export function RecentApplications({
  applications,
  jobs,
  onStatusChange,
  updatingJob,
}: {
  applications: Application[];
  jobs: Job[];
  onStatusChange: (jobId: string, status: Application["status"]) => void;
  updatingJob: string | null;
}) {
  const recent = applications.slice(0, 5);
  return (
    <section className="dashboard-panel" aria-labelledby="recent-applications-heading">
      <div className="dashboard-section-heading">
        <div>
          <p className="ui-eyebrow">Pipeline</p>
          <h2 id="recent-applications-heading">Recent applications</h2>
        </div>
        <Link className="dashboard-view-all" to="/app/applications">
          View all <ArrowRight size={16} aria-hidden="true" />
        </Link>
      </div>
      {recent.length === 0 ? (
        <EmptyState
          description="Save a role or mark an application to start building your pipeline."
          title="No applications yet"
        />
      ) : (
        <div className="dashboard-application-list">
          {recent.map((application) => (
            <ApplicationRow
              application={application}
              job={jobs.find((item) => item.job_id === application.job_id)}
              key={application.job_id}
              onStatusChange={onStatusChange}
              updating={updatingJob === application.job_id}
            />
          ))}
        </div>
      )}
    </section>
  );
}

function ApplicationRow({
  application,
  job,
  onStatusChange,
  updating,
}: {
  application: Application;
  job?: Job;
  onStatusChange: (jobId: string, status: Application["status"]) => void;
  updating: boolean;
}) {
  const title = application.title ?? job?.title ?? "Untitled role";
  const company = application.company ?? job?.company ?? "Company not specified";
  return (
    <div className="dashboard-application-row">
      <div className="dashboard-application-copy">
        <strong>{company}</strong>
        <span>{title}</span>
      </div>
      <ApplicationStatusSelect
        disabled={updating}
        jobTitle={title}
        status={application.status}
        onChange={(status) => onStatusChange(application.job_id, status)}
      />
      <Link
        aria-label={`View ${title}`}
        className="dashboard-application-link"
        to={`/app/jobs/${application.job_id}`}
      >
        <ArrowRight size={17} aria-hidden="true" />
      </Link>
    </div>
  );
}
