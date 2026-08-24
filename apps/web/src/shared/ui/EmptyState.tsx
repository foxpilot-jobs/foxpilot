import type { ReactNode } from "react";

export function EmptyState({
  action,
  children,
  description,
  icon,
  secondaryAction,
  title,
}: {
  action?: ReactNode;
  children?: ReactNode;
  description?: ReactNode;
  icon?: ReactNode;
  secondaryAction?: ReactNode;
  title: ReactNode;
}) {
  return (
    <section className="ui-state ui-empty-state">
      {icon && (
        <div className="ui-state-icon" aria-hidden="true">
          {icon}
        </div>
      )}
      <h2 className="ui-state-title">{title}</h2>
      {description && <p className="ui-state-description">{description}</p>}
      {children}
      {(action || secondaryAction) && (
        <div className="ui-state-actions">
          {action}
          {secondaryAction}
        </div>
      )}
    </section>
  );
}
