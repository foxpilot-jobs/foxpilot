import { Skeleton, SkeletonCard } from "../../../shared/ui/Skeleton";

export function ProfileSkeleton() {
  return (
    <main className="profile-page">
      <div className="profile-skeleton-header">
        <Skeleton className="profile-skeleton-eyebrow" />
        <Skeleton className="profile-skeleton-title" />
        <Skeleton className="profile-skeleton-copy" />
      </div>
      <div className="profile-skeleton-layout">
        <div>
          <SkeletonCard />
          <SkeletonCard />
        </div>
        <div>
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    </main>
  );
}
