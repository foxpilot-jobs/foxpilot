export type Job = {
  job_id?: string;
  source?: string;
  title: string;
  company: string;
  location?: string;
  url?: string;
  description?: string;
  local_relevance?: "TARGET" | "REVIEW" | "EXCLUDE" | null;
  is_active?: boolean;
  last_seen_at?: string | null;
  sources?: Array<{
    source: string;
    source_job_id: string;
    url: string;
    availability_status: "active" | "inactive" | "unknown";
    last_seen_at: string;
    last_checked_at: string | null;
  }>;
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
    gap_analysis?: Array<{
      gap: string;
      severity: "blocking" | "addressable" | "unknown";
      explanation: string;
    }>;
  };
};

export type Application = {
  job_id: string;
  status: "saved" | "applied" | "interviewing" | "rejected" | "offered";
  notes: string;
  title?: string;
  company?: string;
};

export type AuthUser = {
  user_id: string;
  email: string;
  email_verified: boolean;
  session_created: boolean;
};

export type Profile = {
  resume_filename: string;
  profile: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
};

export type BackgroundJob = {
  job_id: string;
  kind: "profile_generation" | "scan" | "matching";
  status: "queued" | "running" | "completed" | "failed";
  result: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
  updated_at: string;
  resume_filename?: string;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function authRequest<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: body ? "POST" : "GET",
    credentials: "include",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Authentication request failed: ${response.status}`);
  }
  return response.status === 204 ? (undefined as T) : (response.json() as Promise<T>);
}

export async function getAuthUser(): Promise<AuthUser | null> {
  const response = await fetch(`${API_BASE}/api/v1/auth/me`, { credentials: "include" });
  if (response.status === 401) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`Unable to check authentication: ${response.status}`);
  }
  return response.json() as Promise<AuthUser>;
}

export function register(email: string, password: string): Promise<AuthUser> {
  return authRequest<AuthUser>("/api/v1/auth/register", { email, password });
}

export function login(email: string, password: string): Promise<AuthUser> {
  return authRequest<AuthUser>("/api/v1/auth/login", { email, password });
}

export function logout(): Promise<void> {
  return fetch(`${API_BASE}/api/v1/auth/logout`, {
    method: "POST",
    credentials: "include",
  }).then(async (response) => {
    if (!response.ok) {
      throw new Error(`Unable to sign out: ${response.status}`);
    }
  });
}

export function verifyEmail(token: string): Promise<AuthUser> {
  return authRequest<AuthUser>("/api/v1/auth/verify-email", { token });
}

export function requestPasswordReset(email: string): Promise<void> {
  return authRequest<void>("/api/v1/auth/request-password-reset", { email });
}

export function resetPassword(token: string, password: string): Promise<AuthUser> {
  return authRequest<AuthUser>("/api/v1/auth/reset-password", { token, password });
}

export async function uploadResume(file: File): Promise<BackgroundJob> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE}/api/v1/profile/resume`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Resume upload failed: ${response.status}`);
  }
  return response.json() as Promise<BackgroundJob>;
}

export async function getProfile(): Promise<Profile> {
  const response = await fetch(`${API_BASE}/api/v1/profile`, { credentials: "include" });
  if (!response.ok) {
    throw new Error(`Unable to load profile: ${response.status}`);
  }
  return response.json() as Promise<Profile>;
}

export async function runMatching(): Promise<BackgroundJob> {
  const response = await fetch(`${API_BASE}/api/v1/profile/match`, {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Matching failed: ${response.status}`);
  }
  return response.json() as Promise<BackgroundJob>;
}

export async function runScan(): Promise<BackgroundJob> {
  const response = await fetch(`${API_BASE}/api/v1/jobs/scan`, {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Job scan failed: ${response.status}`);
  }
  return response.json() as Promise<BackgroundJob>;
}

export async function getBackgroundJob(jobId: string): Promise<BackgroundJob> {
  const response = await fetch(`${API_BASE}/api/v1/profile/jobs/${jobId}`, {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`Unable to check job status: ${response.status}`);
  }
  return response.json() as Promise<BackgroundJob>;
}

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { credentials: "include" });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function getJobs(includeInactive = false): Promise<Job[]> {
  const query = includeInactive ? "?include_inactive=true" : "";
  return request<Job[]>(`/api/v1/jobs${query}`);
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
    credentials: "include",
    body: JSON.stringify({ status, notes: "" }),
  });
  if (!response.ok) {
    throw new Error(`Unable to update application: ${response.status}`);
  }
  return response.json() as Promise<Application>;
}
