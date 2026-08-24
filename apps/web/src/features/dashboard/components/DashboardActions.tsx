import { ArrowRight, BriefcaseBusiness, CircleUserRound, Search } from "lucide-react";
import { Link } from "react-router-dom";

export function DashboardActions({
  hasProfile,
  hasMatches,
  applicationCount,
}: {
  hasProfile: boolean;
  hasMatches: boolean;
  applicationCount: number;
}) {
  const actions = [
    !hasProfile && {
      icon: CircleUserRound,
      title: "Complete your profile",
      description: "Upload your resume to unlock personalized matching.",
      href: "/app/profile",
      label: "Set up profile",
    },
    hasProfile &&
      !hasMatches && {
        icon: Search,
        title: "Find your next opportunity",
        description: "Run a scan and matching job to discover roles aligned with you.",
        href: "/app/profile",
        label: "Run matching",
      },
    hasMatches && {
      icon: Search,
      title: "Explore your matches",
      description: "Review the roles FoxPilot thinks are worth your attention.",
      href: "/app/matches",
      label: "View matches",
    },
    applicationCount > 0 && {
      icon: BriefcaseBusiness,
      title: "Keep your pipeline moving",
      description: "Review the latest statuses across your applications.",
      href: "/app/applications",
      label: "View applications",
    },
  ].filter(Boolean) as Array<{
    icon: typeof CircleUserRound;
    title: string;
    description: string;
    href: string;
    label: string;
  }>;

  if (actions.length === 0) return null;
  return (
    <section className="dashboard-panel dashboard-actions-panel" aria-labelledby="actions-heading">
      <div className="dashboard-section-heading">
        <div>
          <p className="ui-eyebrow">Next steps</p>
          <h2 id="actions-heading">Actions for you</h2>
        </div>
      </div>
      <div className="dashboard-actions-list">
        {actions.map(({ description, href, icon: Icon, label, title }) => (
          <div className="dashboard-action-row" key={title}>
            <span className="dashboard-action-icon">
              <Icon size={19} aria-hidden="true" />
            </span>
            <div className="dashboard-action-copy">
              <strong>{title}</strong>
              <span>{description}</span>
            </div>
            <Link className="dashboard-action-link" to={href}>
              {label}
              <ArrowRight size={16} aria-hidden="true" />
            </Link>
          </div>
        ))}
      </div>
    </section>
  );
}
