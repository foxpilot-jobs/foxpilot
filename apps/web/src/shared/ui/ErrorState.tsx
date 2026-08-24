import { CircleAlert } from "lucide-react";
import type { ReactNode } from "react";
import { EmptyState } from "./EmptyState";

export function ErrorState({
  action,
  description = "Something went wrong. Please try again.",
  title = "Unable to load this view",
}: {
  action?: ReactNode;
  description?: ReactNode;
  title?: ReactNode;
}) {
  return (
    <EmptyState
      action={action}
      description={description}
      icon={<CircleAlert size={24} />}
      title={title}
    />
  );
}
