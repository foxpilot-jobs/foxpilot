import { Search } from "lucide-react";
import { Input } from "../../../../shared/ui/Input";
import { Tabs, type TabItem } from "../../../../shared/ui/Tabs";

const tabs: TabItem[] = [
  { id: "all", label: "All" },
  { id: "saved", label: "Saved" },
  { id: "applied", label: "Applied" },
  { id: "interviewing", label: "Interviewing" },
  { id: "offered", label: "Offered" },
  { id: "rejected", label: "Rejected" },
];

export function ApplicationFilters({
  query,
  status,
  onQueryChange,
  onStatusChange,
}: {
  query: string;
  status: string;
  onQueryChange: (value: string) => void;
  onStatusChange: (value: string) => void;
}) {
  return (
    <div className="applications-filters">
      <div className="applications-search">
        <Search size={18} aria-hidden="true" />
        <Input
          aria-label="Search applications by title or company"
          placeholder="Search title or company"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
        />
      </div>
      <Tabs items={tabs} value={status} onChange={onStatusChange} />
    </div>
  );
}
