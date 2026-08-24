import { ArrowRight, CircleUserRound } from "lucide-react";
import { Link } from "react-router-dom";

export function ProfilePrompt({
  hasProfile,
  resumeFilename,
}: {
  hasProfile: boolean;
  resumeFilename?: string;
}) {
  return (
    <section className={`dashboard-profile-prompt ${hasProfile ? "dashboard-profile-ready" : ""}`}>
      <span className="dashboard-profile-icon">
        <CircleUserRound size={22} aria-hidden="true" />
      </span>
      <div>
        <p className="ui-eyebrow">Career source of truth</p>
        <h2>{hasProfile ? "Your profile is ready" : "Complete your profile"}</h2>
        <p>
          {hasProfile
            ? `${resumeFilename ?? "Resume profile"} is available for matching and career decisions.`
            : "Upload your resume to unlock personalized job matching."}
        </p>
      </div>
      <Link className="dashboard-profile-link" to="/app/profile">
        {hasProfile ? "Manage profile" : "Set up profile"}
        <ArrowRight size={17} aria-hidden="true" />
      </Link>
    </section>
  );
}
