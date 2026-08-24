import type { Application, Job, Match } from "../../../../api";
import { ApplicationCard } from "./ApplicationCard";

const columns = [
  { status: "saved", label: "Saved" },
  { status: "applied", label: "Applied" },
  { status: "interviewing", label: "Interviewing" },
  { status: "offered", label: "Offer" },
  { status: "rejected", label: "Rejected" },
] as const;

export function ApplicationPipeline({
  applications,
  jobs,
  matches,
  statusFilter,
  updatingJob,
  onStatusChange,
}: {
  applications: Application[];
  jobs: Job[];
  matches: Match[];
  statusFilter: string;
  updatingJob: string | null;
  onStatusChange: (jobId: string, status: Application["status"]) => void;
}) {
  const visibleColumns =
    statusFilter === "all" ? columns : columns.filter((column) => column.status === statusFilter);
  const matchByJob = new Map(matches.map((item) => [item.job_id, item.match]));
  const jobById = new Map(jobs.map((job) => [job.job_id, job]));
  return (
    <div className="applications-pipeline">
      {visibleColumns.map((column) => {
        const items = applications.filter((application) => application.status === column.status);
        return (
          <section
            className={`applications-column applications-column-${column.status}`}
            key={column.status}
            aria-labelledby={`applications-${column.status}`}
          >
            <header>
              <h2 id={`applications-${column.status}`}>{column.label}</h2>
              <span>{items.length}</span>
            </header>
            {items.length === 0 ? (
              <p className="applications-column-empty">No {column.label.toLowerCase()} roles yet</p>
            ) : (
              <div className="applications-column-list">
                {items.map((application) => (
                  <ApplicationCard
                    application={application}
                    job={jobById.get(application.job_id)}
                    key={application.job_id}
                    match={matchByJob.get(application.job_id)}
                    updating={updatingJob === application.job_id}
                    onStatusChange={(status) => onStatusChange(application.job_id, status)}
                  />
                ))}
              </div>
            )}
          </section>
        );
      })}
    </div>
  );
}
