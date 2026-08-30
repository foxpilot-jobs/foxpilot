import type { ReactNode } from "react";
import type { Profile } from "../../../api";
import { Badge } from "../../../shared/ui/Badge";

export function ProfileHeader({
  profile,
  hasProfileData,
  workspaceSlot,
}: {
  profile: Profile | null;
  hasProfileData: boolean;
  workspaceSlot?: ReactNode;
}) {
  const readiness = !profile ? "Not configured" : hasProfileData ? "Ready" : "Needs attention";
  const variant =
    readiness === "Ready" ? "success" : readiness === "Needs attention" ? "warning" : "neutral";
  return (
    <header className="profile-page-header">
      {/* Top row: eyebrow + workspace selector right-aligned */}
      <div className="profile-header-top-row">
        <p className="ui-eyebrow">Your career source of truth</p>
        {workspaceSlot && <div className="profile-header-workspace">{workspaceSlot}</div>}
      </div>
      {/* Title + readiness badge on the same baseline */}
      <div className="profile-header-title-row">
        <h1>Your career profile</h1>
        <div className="profile-readiness-chip">
          <span>Profile readiness</span>
          <Badge variant={variant}>{readiness}</Badge>
        </div>
      </div>
      <p className="profile-header-sub">
        FoxPilot uses your experience, skills, and goals to find better-fit opportunities.
      </p>
    </header>
  );
}
