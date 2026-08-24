import { ChevronDown } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";

export function Dropdown({ label, children }: { label: ReactNode; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    const escape = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", escape);
    };
  }, []);
  return (
    <div className="ui-dropdown" ref={root}>
      <button
        aria-expanded={open}
        aria-haspopup="menu"
        className="ui-dropdown-trigger"
        type="button"
        onClick={() => setOpen((current) => !current)}
      >
        {label}
        <ChevronDown size={16} aria-hidden="true" />
      </button>
      {open && (
        <div className="ui-dropdown-menu" role="menu">
          {children}
        </div>
      )}
    </div>
  );
}

export function DropdownItem({ children, onClick }: { children: ReactNode; onClick?: () => void }) {
  return (
    <button className="ui-dropdown-item" role="menuitem" type="button" onClick={onClick}>
      {children}
    </button>
  );
}
