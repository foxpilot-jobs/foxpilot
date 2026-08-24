import { ArrowRight, CircleCheck, CircleUserRound } from "lucide-react";
import { Link } from "react-router-dom";
import type { Profile } from "../../../api";
import { Badge } from "../../../shared/ui/Badge";

export function ProfileReadiness({
  profile,
  hasProfileData,
}: {
  profile: Profile | null;
  hasProfileData: boolean;
}) {
  if (!profile)
    return (
      <section className="profile-readiness profile-readiness-empty">
        <span className="profile-readiness-icon">
          <CircleUserRound size={22} aria-hidden="true" />
        </span>
        <div>
          <p className="ui-eyebrow">Start here</p>
          <h2>Build your FoxPilot profile</h2>
          <p>Upload your resume and we&apos;ll turn it into a structured career profile.</p>
        </div>
        <Link className="ui-button ui-button-primary ui-button-md" to="#resume">
          Upload resume
          <ArrowRight size={16} aria-hidden="true" />
        </Link>
      </section>
    );
  return (
    <section
      className={`profile-readiness ${hasProfileData ? "profile-readiness-ready" : "profile-readiness-attention"}`}
    >
      <span className="profile-readiness-icon">
        <CircleCheck size={22} aria-hidden="true" />
      </span>
      <div>
        <p className="ui-eyebrow">Profile status</p>
        <h2>{hasProfileData ? "Profile ready" : "Profile needs attention"}</h2>
        <p>
          {hasProfileData
            ? "FoxPilot has enough context to personalize your job discovery."
            : "Review your extracted profile and replace your resume if important details are missing."}
        </p>
      </div>
      <Badge variant={hasProfileData ? "success" : "warning"}>
        {hasProfileData ? "Ready for matching" : "Review profile"}
      </Badge>
    </section>
  );
}
