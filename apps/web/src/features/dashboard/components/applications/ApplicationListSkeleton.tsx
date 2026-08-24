import { SkeletonCard } from "../../../../shared/ui/Skeleton";

export function ApplicationListSkeleton() {
  return (
    <div className="applications-skeleton" aria-label="Loading applications" role="status">
      {[1, 2, 3, 4, 5].map((item) => (
        <SkeletonCard key={item} />
      ))}
    </div>
  );
}
