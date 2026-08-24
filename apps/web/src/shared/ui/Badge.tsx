import type { ReactNode } from "react";

export function Badge({
  children,
  variant = "neutral",
}: {
  children: ReactNode;
  variant?: "neutral" | "success" | "warning" | "error" | "info" | "brand";
}) {
  return <span className={`ui-badge ui-badge-${variant}`}>{children}</span>;
}
