export type Job = {
  job_id?: string;
  source?: string;
  title: string;
  company: string;
  location?: string;
  url?: string;
  description?: string;
  local_relevance?: "TARGET" | "REVIEW" | "EXCLUDE" | null;
};

export type Match = {
  job_id: string;
  job: Job;
  match: {
    match_score: number;
    recommendation: "APPLY" | "CONSIDER" | "SKIP";
    reasons: string[];
    matching_skills: string[];
    missing_skills: string[];
    experience_match: string;
    concerns: string[];
  };
};

export type Application = {
  job_id: string;
  status: "saved" | "applied" | "interviewing" | "rejected" | "offered";
  notes: string;
  title?: string;
  company?: string;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function getJobs(): Promise<Job[]> {
  return request<Job[]>("/api/v1/jobs?relevance=TARGET");
}

export function getMatches(): Promise<Match[]> {
  return request<Match[]>("/api/v1/matches");
}

export function getApplications(): Promise<Application[]> {
  return request<Application[]>("/api/v1/applications");
}

export async function updateApplication(
  jobId: string,
  status: Application["status"],
): Promise<Application> {
  const response = await fetch(`${API_BASE}/api/v1/jobs/${jobId}/application`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, notes: "" }),
  });
  if (!response.ok) {
    throw new Error(`Unable to update application: ${response.status}`);
  }
  return response.json() as Promise<Application>;
}
