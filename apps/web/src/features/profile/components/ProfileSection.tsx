import type { ReactNode } from "react";

export function ProfileSection({
  children,
  label,
  title,
}: {
  children: ReactNode;
  label?: string;
  title: string;
}) {
  return (
    <section className="profile-data-section">
      <div className="profile-section-heading">
        {label && <p className="ui-eyebrow">{label}</p>}
        <h3>{title}</h3>
      </div>
      {children}
    </section>
  );
}
