import { SkeletonCard } from "../../../../shared/ui/Skeleton";

export function MatchListSkeleton() {
  return (
    <div className="matches-skeleton" aria-label="Loading matches" role="status">
      {[1, 2, 3, 4, 5].map((item) => (
        <SkeletonCard key={item} />
      ))}
    </div>
  );
}
