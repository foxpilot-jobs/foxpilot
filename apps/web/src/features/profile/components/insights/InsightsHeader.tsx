import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

export function InsightsHeader() {
  return (
    <header className="profile-insights-header">
      <div>
        <p className="ui-eyebrow">Career intelligence</p>
        <h1>Profile Insights</h1>
        <p>
          Understand how your experience, skills, and goals shape your FoxPilot recommendations.
        </p>
      </div>
      <Link className="profile-insights-back" to="/app/profile">
        <ArrowLeft size={16} aria-hidden="true" />
        Back to Profile
      </Link>
    </header>
  );
}
