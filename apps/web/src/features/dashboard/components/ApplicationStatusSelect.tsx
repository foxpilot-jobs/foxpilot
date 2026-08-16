import type { Application } from "../../../api";
import { formatStatus, statuses } from "../constants";

type ApplicationStatusSelectProps = {
  jobTitle: string;
  status?: Application["status"];
  disabled: boolean;
  onChange: (status: Application["status"]) => void;
};

export function ApplicationStatusSelect({
  disabled,
  jobTitle,
  onChange,
  status,
}: ApplicationStatusSelectProps) {
  return (
    <select
      aria-label={`Application status for ${jobTitle}`}
      value={status ?? ""}
      disabled={disabled}
      onChange={(event) => onChange(event.target.value as Application["status"])}
    >
      <option value="">Track status</option>
      {statuses.map((option) => (
        <option key={option} value={option}>
          {formatStatus(option)}
        </option>
      ))}
    </select>
  );
}
