import { ArrowDownUp } from "lucide-react";
import { Tabs, type TabItem } from "../../../../shared/ui/Tabs";

const recommendationTabs: TabItem[] = [
  { id: "all", label: "All" },
  { id: "APPLY", label: "Apply" },
  { id: "CONSIDER", label: "Consider" },
  { id: "SKIP", label: "Skip" },
];

export function MatchFilters({
  recommendation,
  sort,
  onRecommendationChange,
  onSortChange,
}: {
  recommendation: string;
  sort: string;
  onRecommendationChange: (value: string) => void;
  onSortChange: (value: string) => void;
}) {
  return (
    <div className="matches-controls">
      <Tabs items={recommendationTabs} value={recommendation} onChange={onRecommendationChange} />
      <label className="matches-sort">
        <ArrowDownUp size={16} aria-hidden="true" />
        <span>Sort</span>
        <select
          aria-label="Sort matches"
          value={sort}
          onChange={(event) => onSortChange(event.target.value)}
        >
          <option value="score">Best match</option>
          <option value="newest">Newest</option>
          <option value="company">Company</option>
          <option value="title">Title</option>
        </select>
      </label>
    </div>
  );
}
