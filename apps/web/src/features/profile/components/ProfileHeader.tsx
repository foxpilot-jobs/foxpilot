import type { ReactNode } from "react";
import type { Profile } from "../../../api";
import { Badge } from "../../../shared/ui/Badge";

export function ProfileHeader({
  profile,
  hasProfileData,
  workspaceSlot,
  dangerActions,
}: {
  profile: Profile | null;
  hasProfileData: boolean;
  workspaceSlot?: ReactNode;
  dangerActions?: ReactNode;
}) {
  const readiness = !profile ? "Not configured" : hasProfileData ? "Ready" : "Needs attention";
  const variant =
    readiness === "Ready" ? "success" : readiness === "Needs attention" ? "warning" : "neutral";
  return (
    <header className="profile-page-header">
      <div className="profile-header-layout">
        <div className="profile-header-copy">
          <p className="ui-eyebrow">Your career source of truth</p>
          <h1>Your career profile</h1>
          <p>FoxPilot uses your experience, skills, and goals to find better-fit opportunities.</p>
        </div>
        <div className="profile-header-panel">
          {workspaceSlot}
          <div className="profile-readiness-chip">
            <span>Profile readiness</span>
            <Badge variant={variant}>{readiness}</Badge>
          </div>
          {dangerActions && <div className="profile-danger-actions">{dangerActions}</div>}
        </div>
      </div>
    </header>
  );
}
