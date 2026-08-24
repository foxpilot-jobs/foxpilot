import { Spinner } from "./Spinner";

export function LoadingState({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="ui-loading-state" role="status" aria-live="polite">
      <Spinner />
      <span>{label}</span>
    </div>
  );
}
