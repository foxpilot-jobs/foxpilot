import { useRef, useState, type KeyboardEvent, type ReactNode } from "react";

export type TabItem = { id: string; label: ReactNode; icon?: ReactNode; badge?: ReactNode };

export function Tabs({
  items,
  onChange,
  value,
}: {
  items: TabItem[];
  onChange: (value: string) => void;
  value: string;
}) {
  const [focusedIndex, setFocusedIndex] = useState(
    Math.max(
      0,
      items.findIndex((item) => item.id === value),
    ),
  );
  const refs = useRef<Array<HTMLButtonElement | null>>([]);
  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (!items.length || !["ArrowRight", "ArrowLeft", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const direction = event.key === "ArrowLeft" ? -1 : event.key === "ArrowRight" ? 1 : 0;
    const nextIndex =
      event.key === "Home"
        ? 0
        : event.key === "End"
          ? items.length - 1
          : (focusedIndex + direction + items.length) % items.length;
    setFocusedIndex(nextIndex);
    refs.current[nextIndex]?.focus();
    onChange(items[nextIndex].id);
  };

  return (
    <div className="ui-tabs" role="tablist" aria-label="Navigation tabs">
      {items.map((item, index) => (
        <button
          aria-selected={item.id === value}
          className={`ui-tab ${item.id === value ? "ui-tab-active" : ""}`}
          key={item.id}
          ref={(element) => {
            refs.current[index] = element;
          }}
          role="tab"
          tabIndex={item.id === value ? 0 : -1}
          type="button"
          onClick={() => {
            setFocusedIndex(index);
            onChange(item.id);
          }}
          onKeyDown={handleKeyDown}
        >
          {item.icon}
          <span>{item.label}</span>
          {item.badge}
        </button>
      ))}
    </div>
  );
}
