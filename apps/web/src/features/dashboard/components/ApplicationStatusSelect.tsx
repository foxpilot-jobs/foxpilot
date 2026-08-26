import { Check, ChevronDown } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { Application } from "../../../api";
import { formatStatus, statuses } from "../constants";

type ApplicationStatusSelectProps = {
  jobTitle: string;
  status?: Application["status"];
  disabled: boolean;
  onChange: (status: Application["status"]) => void;
};

const options: Array<{ value: Application["status"] | ""; label: string }> = [
  { value: "", label: "Track status" },
  ...statuses.map((s) => ({ value: s, label: formatStatus(s) })),
];

export function ApplicationStatusSelect({
  disabled,
  jobTitle,
  onChange,
  status,
}: ApplicationStatusSelectProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  const current = options.find((o) => o.value === (status ?? "")) ?? options[0];

  useEffect(() => {
    if (!open) return;
    function onClickOutside(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function onEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    document.addEventListener("keydown", onEscape);
    return () => {
      document.removeEventListener("mousedown", onClickOutside);
      document.removeEventListener("keydown", onEscape);
    };
  }, [open]);

  function select(value: string) {
    if (value) {
      onChange(value as Application["status"]);
    }
    setOpen(false);
    triggerRef.current?.focus();
  }

  return (
    <div className="status-select" ref={ref}>
      <button
        ref={triggerRef}
        type="button"
        className="status-select-trigger"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`Application status for ${jobTitle}`}
        disabled={disabled}
        onClick={() => setOpen((prev) => !prev)}
      >
        <span>{current.label}</span>
        <ChevronDown size={14} aria-hidden="true" />
      </button>
      {open && (
        <ul className="status-select-menu" role="listbox" aria-label="Application status">
          {options.map((option) => (
            <li key={option.value}>
              <button
                type="button"
                className={`status-select-option${option.value === (status ?? "") ? " status-select-option-active" : ""}`}
                role="option"
                aria-selected={option.value === (status ?? "")}
                onClick={() => select(option.value)}
              >
                <span>{option.label}</span>
                {option.value === (status ?? "") && (
                  <Check size={14} aria-hidden="true" />
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
