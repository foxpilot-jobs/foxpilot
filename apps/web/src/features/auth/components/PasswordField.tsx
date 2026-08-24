import { Eye, EyeOff } from "lucide-react";
import { useId, useState } from "react";

export function PasswordField({
  autoComplete,
  error,
  help,
  label = "Password",
  onChange,
  value,
}: {
  autoComplete: string;
  error?: string;
  help?: string;
  label?: string;
  onChange: (value: string) => void;
  value: string;
}) {
  const [visible, setVisible] = useState(false);
  const inputId = useId();
  const helpId = `${inputId}-help`;
  const errorId = `${inputId}-error`;
  const describedBy = error ? errorId : help ? helpId : undefined;
  return (
    <div className="ui-field auth-password-field">
      <label className="ui-field-label" htmlFor={inputId}>
        {label}
        <span aria-hidden="true"> *</span>
      </label>
      <div className="auth-password-input">
        <input
          autoComplete={autoComplete}
          aria-describedby={describedBy}
          aria-invalid={Boolean(error)}
          aria-required="true"
          className="ui-input"
          id={inputId}
          type={visible ? "text" : "password"}
          value={value}
          onChange={(event) => onChange(event.target.value)}
        />
        <button
          aria-label={visible ? "Hide password" : "Show password"}
          className="auth-password-toggle"
          type="button"
          onClick={() => setVisible((current) => !current)}
        >
          {visible ? <EyeOff size={17} aria-hidden="true" /> : <Eye size={17} aria-hidden="true" />}
        </button>
      </div>
      {error ? (
        <span className="ui-field-message ui-field-error" id={errorId} role="alert">
          {error}
        </span>
      ) : (
        help && (
          <span className="ui-field-message" id={helpId}>
            {help}
          </span>
        )
      )}
    </div>
  );
}
