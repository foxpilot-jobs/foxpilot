import type { ButtonHTMLAttributes } from "react";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "quiet" | "text";
};

export function Button({ className = "", variant = "primary", ...props }: ButtonProps) {
  const variantClass =
    variant === "primary" ? "primary-button" : variant === "quiet" ? "ghost-button" : "text-button";
  return <button {...props} className={`${variantClass} ${className}`.trim()} />;
}
