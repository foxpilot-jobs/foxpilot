import type { Application } from "../../api";

export const statuses: Array<Application["status"]> = [
  "saved",
  "applied",
  "interviewing",
  "rejected",
  "offered",
];

export function formatStatus(status: string) {
  return status.charAt(0).toUpperCase() + status.slice(1);
}
