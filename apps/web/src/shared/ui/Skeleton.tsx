export function Skeleton({ className = "" }: { className?: string }) {
  return <span className={`ui-skeleton ${className}`.trim()} aria-hidden="true" />;
}

export function SkeletonText({ lines = 2 }: { lines?: number }) {
  return (
    <span className="ui-skeleton-text" aria-hidden="true">
      {Array.from({ length: lines }, (_, index) => (
        <Skeleton className={index === lines - 1 ? "ui-skeleton-short" : ""} key={index} />
      ))}
    </span>
  );
}

export function SkeletonCard() {
  return (
    <div className="ui-skeleton-card" aria-hidden="true">
      <Skeleton className="ui-skeleton-label" />
      <Skeleton className="ui-skeleton-heading" />
      <SkeletonText lines={3} />
    </div>
  );
}

export function SkeletonAvatar() {
  return <Skeleton className="ui-skeleton-avatar" />;
}

export function SkeletonRow() {
  return (
    <div className="ui-skeleton-row" aria-hidden="true">
      <SkeletonAvatar />
      <SkeletonText lines={2} />
    </div>
  );
}
