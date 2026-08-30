import { X } from "lucide-react";
import { useEffect, useId, useRef, type ReactNode } from "react";
import { Button } from "./Button";

export function Modal({
  children,
  onClose,
  open,
  title,
}: {
  children: ReactNode;
  onClose: () => void;
  open: boolean;
  title: string;
}) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    document.body.classList.add("ui-scroll-locked");
    // Only focus the dialog container if focus is not already inside it
    // (e.g. an autoFocus input). Moving focus to the container steals it
    // from inputs on every state update that re-triggers the effect.
    if (!dialogRef.current?.contains(document.activeElement)) {
      dialogRef.current?.focus();
    }
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.classList.remove("ui-scroll-locked");
    };
  }, [onClose, open]);

  if (!open) return null;

  return (
    <div className="ui-modal-overlay" onClick={onClose}>
      <div
        aria-labelledby={titleId}
        aria-modal="true"
        className="ui-modal"
        ref={dialogRef}
        role="dialog"
        tabIndex={-1}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="ui-modal-header">
          <h2 className="ui-modal-title" id={titleId}>
            {title}
          </h2>
          <Button
            aria-label="Close dialog"
            icon={<X size={18} />}
            iconOnly
            size="sm"
            variant="ghost"
            onClick={onClose}
          />
        </div>
        <div className="ui-modal-body">{children}</div>
      </div>
    </div>
  );
}

export function ModalActions({ children }: { children: ReactNode }) {
  return <div className="ui-modal-actions">{children}</div>;
}
