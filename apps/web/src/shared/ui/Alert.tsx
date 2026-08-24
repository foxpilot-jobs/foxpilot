import { AlertCircle, CheckCircle2, Info, TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";

const icons = {
  success: CheckCircle2,
  info: Info,
  warning: TriangleAlert,
  error: AlertCircle,
};

export function Alert({
  children,
  title,
  variant = "info",
}: {
  children: ReactNode;
  title?: string;
  variant?: keyof typeof icons;
}) {
  const Icon = icons[variant];
  return (
    <div className={`ui-alert ui-alert-${variant}`} role={variant === "error" ? "alert" : "status"}>
      <Icon className="ui-alert-icon" size={20} aria-hidden="true" />
      <div>
        {title && <strong className="ui-alert-title">{title}</strong>}
        <div>{children}</div>
      </div>
    </div>
  );
}
