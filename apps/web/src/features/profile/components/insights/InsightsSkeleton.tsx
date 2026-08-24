import { SkeletonCard } from "../../../../shared/ui/Skeleton";

export function InsightsSkeleton() {
  return (
    <main className="profile-insights-page">
      <div className="insights-skeleton-header">
        <SkeletonCard />
      </div>
      <div className="insights-skeleton-grid">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    </main>
  );
}
