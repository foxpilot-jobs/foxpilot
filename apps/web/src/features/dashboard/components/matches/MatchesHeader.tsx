import { Search } from "lucide-react";
import type { ChangeEvent } from "react";
import { Input } from "../../../../shared/ui/Input";

export function MatchesHeader({
  query,
  onQueryChange,
}: {
  query: string;
  onQueryChange: (query: string) => void;
}) {
  return (
    <header className="matches-header">
      <div>
        <p className="ui-eyebrow">Discover with evidence</p>
        <h1>Find the opportunities that fit you.</h1>
        <p>
          FoxPilot analyzes your profile against available roles and explains why each opportunity
          is worth your attention.
        </p>
      </div>
      <div className="matches-search">
        <Search size={19} aria-hidden="true" />
        <Input
          aria-label="Search matches"
          placeholder="Search title, company, or location"
          value={query}
          onChange={(event: ChangeEvent<HTMLInputElement>) => onQueryChange(event.target.value)}
        />
      </div>
    </header>
  );
}
