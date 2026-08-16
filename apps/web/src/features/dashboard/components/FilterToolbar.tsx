import { formatStatus, statuses } from "../constants";

type FilterToolbarProps = {
  query: string;
  statusFilter: string;
  onQueryChange: (query: string) => void;
  onStatusChange: (status: string) => void;
};

export function FilterToolbar({
  onQueryChange,
  onStatusChange,
  query,
  statusFilter,
}: FilterToolbarProps) {
  return (
    <section className="toolbar" aria-label="Shortlist filters">
      <input
        aria-label="Search jobs"
        placeholder="Search title, company, location"
        value={query}
        onChange={(event) => onQueryChange(event.target.value)}
      />
      <div className="filter-tabs">
        {(["all", ...statuses] as const).map((status) => (
          <button
            className={statusFilter === status ? "active" : ""}
            key={status}
            type="button"
            onClick={() => onStatusChange(status)}
          >
            {status === "all" ? "All" : formatStatus(status)}
          </button>
        ))}
      </div>
    </section>
  );
}
