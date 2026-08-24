import type { LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";

export function DashboardMetricCard({
  icon: Icon,
  label,
  value,
  supportingText,
  href,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  supportingText: string;
  href?: string;
}) {
  const content = (
    <>
      <div className="dashboard-metric-topline">
        <span className="dashboard-metric-icon">
          <Icon size={18} aria-hidden="true" />
        </span>
        <span className="dashboard-metric-label">{label}</span>
      </div>
      <strong className="dashboard-metric-value">{value}</strong>
      <span className="dashboard-metric-supporting">{supportingText}</span>
    </>
  );
  return href ? (
    <Link className="dashboard-metric-card" to={href}>
      {content}
    </Link>
  ) : (
    <div className="dashboard-metric-card">{content}</div>
  );
}
