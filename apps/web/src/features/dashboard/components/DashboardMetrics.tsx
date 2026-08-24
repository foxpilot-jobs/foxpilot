import { BriefcaseBusiness, CircleUserRound, Sparkles } from "lucide-react";
import type { Match, Profile } from "../../../api";
import { DashboardMetricCard } from "./DashboardMetricCard";

export function DashboardMetrics({
  applications,
  matches,
  profile,
}: {
  applications: number;
  matches: Match[];
  profile: Profile | null;
}) {
  const topMatch = [...matches].sort(
    (left, right) => right.match.match_score - left.match.match_score,
  )[0];
  return (
    <section className="dashboard-metrics" aria-label="Career summary">
      <DashboardMetricCard
        icon={CircleUserRound}
        label="Profile"
        supportingText={profile ? profile.resume_filename : "Resume needed to personalize matches"}
        value={profile ? "Ready" : "Not set up"}
        href="/app/profile"
      />
      <DashboardMetricCard
        icon={Sparkles}
        label="Top match"
        supportingText={
          topMatch
            ? `${topMatch.job.company} · ${topMatch.job.title}`
            : "Run matching to see your strongest fit"
        }
        value={topMatch ? `${Math.round(topMatch.match.match_score)}%` : "—"}
        href={topMatch ? `/app/jobs/${topMatch.job_id}` : "/app/matches"}
      />
      <DashboardMetricCard
        icon={BriefcaseBusiness}
        label="New matches"
        supportingText={
          matches.length ? "Personalized roles ready to review" : "No personalized matches yet"
        }
        value={`${matches.length}`}
        href="/app/matches"
      />
      <DashboardMetricCard
        icon={BriefcaseBusiness}
        label="Applications"
        supportingText={
          applications ? "Roles in your application pipeline" : "Track your first application"
        }
        value={`${applications}`}
        href="/app/applications"
      />
    </section>
  );
}
