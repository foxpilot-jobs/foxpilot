import { BriefcaseBusiness } from "lucide-react";

export function ApplicationHeader() {
  return (
    <header className="applications-header">
      <div className="applications-header-icon">
        <BriefcaseBusiness size={20} aria-hidden="true" />
      </div>
      <div>
        <p className="ui-eyebrow">Track your progress</p>
        <h1>Applications</h1>
        <p>Keep track of every opportunity from saved to offer.</p>
      </div>
    </header>
  );
}
