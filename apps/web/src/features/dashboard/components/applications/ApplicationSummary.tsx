import type { Application } from "../../../../api";

const summary = [
  { key: "saved", label: "Saved" },
  { key: "applied", label: "Applied" },
  { key: "interviewing", label: "Interviewing" },
  { key: "offered", label: "Offers" },
] as const;

export function ApplicationSummary({ applications }: { applications: Application[] }) {
  return (
    <section className="applications-summary" aria-label="Application summary">
      {summary.map(({ key, label }) => (
        <div key={key}>
          <strong>{applications.filter((application) => application.status === key).length}</strong>
          <span>{label}</span>
        </div>
      ))}
      <div className="applications-summary-rejected">
        <strong>
          {applications.filter((application) => application.status === "rejected").length}
        </strong>
        <span>Rejected</span>
      </div>
    </section>
  );
}
