import type { ReactNode } from "react";

export function Tooltip({ children, content }: { children: ReactNode; content: string }) {
  return (
    <span className="ui-tooltip">
      <span className="ui-tooltip-trigger">{children}</span>
      <span className="ui-tooltip-content" role="tooltip">
        {content}
      </span>
    </span>
  );
}
