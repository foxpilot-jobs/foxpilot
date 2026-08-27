import { Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getGreeting } from "./greeting";

export function DashboardHeader({ email }: { email: string }) {
  const firstName = formatFirstName(email);
  const [greeting, setGreeting] = useState(() => getGreeting());

  useEffect(() => {
    const updateGreeting = () => setGreeting(getGreeting());
    const timer = window.setInterval(updateGreeting, 60_000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <header className="dashboard-header">
      <div>
        <p className="ui-eyebrow">Career workspace</p>
        <h1 className="dashboard-title">
          {greeting}, {firstName}.
        </h1>
        <p className="dashboard-subtitle">Here&apos;s what&apos;s happening with your career.</p>
      </div>
      <Link className="dashboard-header-link" to="/app/matches">
        <Sparkles size={17} aria-hidden="true" />
        Explore matches
      </Link>
    </header>
  );
}

function formatFirstName(email: string) {
  const localPart = email
    .split("@", 1)[0]
    ?.replace(/[._-]+/g, " ")
    .trim();
  if (!localPart) return "there";
  return localPart
    .split(" ")
    .map((part) => `${part.slice(0, 1).toUpperCase()}${part.slice(1).toLowerCase()}`)
    .join(" ");
}
