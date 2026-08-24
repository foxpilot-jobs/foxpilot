import { ArrowRight, Lightbulb } from "lucide-react";
import { Link } from "react-router-dom";

export function ProfileInsightsLink() {
  return (
    <section className="profile-insights-link">
      <span className="profile-insights-icon">
        <Lightbulb size={19} aria-hidden="true" />
      </span>
      <div>
        <h2>Your profile powers your recommendations</h2>
        <p>
          FoxPilot uses your experience, skills, target roles, and preferences to evaluate
          opportunities.
        </p>
      </div>
      <Link to="/app/profile/insights">
        View profile insights
        <ArrowRight size={16} aria-hidden="true" />
      </Link>
    </section>
  );
}
