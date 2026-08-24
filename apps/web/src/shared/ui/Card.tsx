import type { HTMLAttributes, ReactNode } from "react";

type CardProps = HTMLAttributes<HTMLElement> & {
  variant?: "default" | "interactive" | "elevated" | "selected" | "warning" | "success";
};

export function Card({ className = "", variant = "default", ...props }: CardProps) {
  return <section {...props} className={`ui-card ui-card-${variant} ${className}`.trim()} />;
}

export function CardHeader({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div {...props} className={`ui-card-header ${className}`.trim()} />;
}

export function CardTitle({ className = "", ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return <h3 {...props} className={`ui-card-title ${className}`.trim()} />;
}

export function CardDescription({
  className = "",
  ...props
}: HTMLAttributes<HTMLParagraphElement>) {
  return <p {...props} className={`ui-card-description ${className}`.trim()} />;
}

export function CardContent({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div {...props} className={`ui-card-content ${className}`.trim()} />;
}

export function CardFooter({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div {...props} className={`ui-card-footer ${className}`.trim()} />;
}

export function CardActions({ children }: { children: ReactNode }) {
  return <div className="ui-card-actions">{children}</div>;
}
