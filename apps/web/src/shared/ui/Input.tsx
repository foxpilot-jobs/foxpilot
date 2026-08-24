import { useId, type InputHTMLAttributes, type ReactNode } from "react";

export type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  hint?: ReactNode;
  error?: ReactNode;
  success?: ReactNode;
  requiredIndicator?: boolean;
};

export function Input({
  error,
  hint,
  id,
  label,
  requiredIndicator = false,
  success,
  ...props
}: InputProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const descriptionId = `${inputId}-description`;
  const describedBy = hint || error || success ? descriptionId : undefined;

  return (
    <div className="ui-field">
      {label && (
        <label className="ui-field-label" htmlFor={inputId}>
          {label}
          {requiredIndicator && <span aria-hidden="true"> *</span>}
        </label>
      )}
      <input
        {...props}
        id={inputId}
        className="ui-input"
        aria-describedby={describedBy}
        aria-invalid={Boolean(error)}
      />
      {(error || hint || success) && (
        <span
          className={`ui-field-message ${error ? "ui-field-error" : success ? "ui-field-success" : ""}`}
          id={descriptionId}
          role={error ? "alert" : undefined}
        >
          {error ?? success ?? hint}
        </span>
      )}
    </div>
  );
}
