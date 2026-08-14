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

export type AuthUser = {
  user_id: string;
  email: string;
  email_verified: boolean;
  session_created: boolean;
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
  return authRequest<void>("/api/v1/auth/logout");
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

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { credentials: "include" });
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
    credentials: "include",
    body: JSON.stringify({ status, notes: "" }),
  });
  if (!response.ok) {
    throw new Error(`Unable to update application: ${response.status}`);
  }
  return response.json() as Promise<Application>;
}
