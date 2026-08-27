import { Check, ChevronDown } from "lucide-react";
import { useEffect, useRef, useState } from "react";

const options = [
  { value: "score", label: "Best match" },
  { value: "newest", label: "Newest" },
  { value: "company", label: "Company" },
  { value: "title", label: "Title" },
] as const;

export function MatchSortSelect({
  sort,
  onChange,
}: {
  sort: string;
  onChange: (value: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const current = options.find((option) => option.value === sort) ?? options[0];

  useEffect(() => {
    if (!open) return;
    const closeOnOutsideClick = (event: MouseEvent) => {
      if (!ref.current?.contains(event.target as Node)) setOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("mousedown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  function select(value: string) {
    onChange(value);
    setOpen(false);
    triggerRef.current?.focus();
  }

  return (
    <div className="matches-sort-select" ref={ref}>
      <button
        ref={triggerRef}
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-label="Sort matches"
        className="matches-sort-trigger"
        type="button"
        onClick={() => setOpen((value) => !value)}
      >
        <span>{current.label}</span>
        <ChevronDown size={14} aria-hidden="true" />
      </button>
      {open && (
        <ul className="matches-sort-menu" role="listbox" aria-label="Sort matches">
          {options.map((option) => (
            <li key={option.value}>
              <button
                aria-selected={option.value === sort}
                className={`matches-sort-option${option.value === sort ? " matches-sort-option-active" : ""}`}
                role="option"
                type="button"
                onClick={() => select(option.value)}
              >
                <span>{option.label}</span>
                {option.value === sort && <Check size={14} aria-hidden="true" />}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
