import { CheckCircle2, Info, TriangleAlert, X } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "./Button";

const icons = {
  success: CheckCircle2,
  info: Info,
  warning: TriangleAlert,
  error: TriangleAlert,
};

export function Toast({
  children,
  onDismiss,
  title,
  variant = "info",
}: {
  children: ReactNode;
  onDismiss?: () => void;
  title?: string;
  variant?: keyof typeof icons;
}) {
  const Icon = icons[variant];
  return (
    <div className={`ui-toast ui-toast-${variant}`} role={variant === "error" ? "alert" : "status"}>
      <Icon className="ui-toast-icon" size={20} aria-hidden="true" />
      <div className="ui-toast-body">
        {title && <strong>{title}</strong>}
        <div>{children}</div>
      </div>
      {onDismiss && (
        <Button
          aria-label="Dismiss notification"
          icon={<X size={16} />}
          iconOnly
          size="sm"
          variant="ghost"
          onClick={onDismiss}
        />
      )}
    </div>
  );
}
