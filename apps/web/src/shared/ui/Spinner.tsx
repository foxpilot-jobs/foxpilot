import { LoaderCircle } from "lucide-react";

export function Spinner({ size = 20, label }: { size?: number; label?: string }) {
  return (
    <LoaderCircle className="ui-spinner" size={size} aria-label={label} aria-hidden={!label} />
  );
}
