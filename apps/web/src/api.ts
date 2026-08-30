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
  canonical_content_hash?: string;
  normalized_company?: string;
  normalized_location?: string;
  active_listing_count?: number;
  sources?: Array<{
    source: string;
    source_job_id: string;
    source_requisition_id: string;
    url: string;
    source_url_history: string[];
    availability_status: "active" | "inactive" | "unknown";
    last_seen_at: string;
    last_checked_at: string | null;
  }>;
};

export type JobDetail = Job & {
  match?: Match["match"] | null;
  application?: Application | null;
};

export function availableJobSources(job: Job) {
  return (job.sources ?? []).filter(
    (source) => source.availability_status !== "inactive" && Boolean(source.url),
  );
}

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
  status: "queued" | "running" | "completed" | "failed" | "dead_letter";
  result: Record<string, unknown> | null;
  error: string | null;
  error_class?: "retryable" | "permanent" | null;
  attempt?: number;
  max_attempts?: number;
  progress?: Record<string, unknown> | null;
  started_at?: string | null;
  created_at: string;
  updated_at: string;
  resume_filename?: string;
};

export type PaginatedResponse<T> = {
  items: T[];
  next_cursor: string | null;
  total: number;
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

export function getJobs(
  params: {
    includeInactive?: boolean;
    limit?: number;
    cursor?: string;
    query?: string;
    source?: string;
    location?: string;
    work_type?: string;
    sort?: string;
    relevance?: string;
  } = {},
): Promise<PaginatedResponse<Job>> {
  const searchParams = new URLSearchParams();
  if (params.includeInactive) searchParams.set("include_inactive", "true");
  if (params.limit) searchParams.set("limit", String(params.limit));
  if (params.cursor) searchParams.set("cursor", params.cursor);
  if (params.query) searchParams.set("query", params.query);
  if (params.source) searchParams.set("source", params.source);
  if (params.location) searchParams.set("location", params.location);
  if (params.work_type) searchParams.set("work_type", params.work_type);
  if (params.sort) searchParams.set("sort", params.sort);
  if (params.relevance) searchParams.set("relevance", params.relevance);
  const qs = searchParams.toString();
  return request<PaginatedResponse<Job>>(`/api/v1/jobs${qs ? `?${qs}` : ""}`);
}

export async function getJob(jobId: string): Promise<JobDetail | null> {
  const response = await fetch(`${API_BASE}/api/v1/jobs/${encodeURIComponent(jobId)}`, {
    credentials: "include",
  });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`Unable to load job: ${response.status}`);
  return response.json() as Promise<JobDetail>;
}

export function getMatches(
  params: {
    limit?: number;
    cursor?: string;
    query?: string;
    recommendation?: string;
    sort?: string;
  } = {},
): Promise<PaginatedResponse<Match>> {
  const searchParams = new URLSearchParams();
  if (params.limit) searchParams.set("limit", String(params.limit));
  if (params.cursor) searchParams.set("cursor", params.cursor);
  if (params.query) searchParams.set("query", params.query);
  if (params.recommendation) searchParams.set("recommendation", params.recommendation);
  if (params.sort) searchParams.set("sort", params.sort);
  const qs = searchParams.toString();
  return request<PaginatedResponse<Match>>(`/api/v1/matches${qs ? `?${qs}` : ""}`);
}

export function getApplications(
  params: {
    limit?: number;
    cursor?: string;
    query?: string;
    application_status?: string;
    sort?: string;
  } = {},
): Promise<PaginatedResponse<Application>> {
  const searchParams = new URLSearchParams();
  if (params.limit) searchParams.set("limit", String(params.limit));
  if (params.cursor) searchParams.set("cursor", params.cursor);
  if (params.query) searchParams.set("query", params.query);
  if (params.application_status) searchParams.set("application_status", params.application_status);
  if (params.sort) searchParams.set("sort", params.sort);
  const qs = searchParams.toString();
  return request<PaginatedResponse<Application>>(`/api/v1/applications${qs ? `?${qs}` : ""}`);
}

// -- Workspaces --------------------------------------------------------------

export type Workspace = {
  workspace_id: string;
  name: string;
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
};

export async function listWorkspaces(): Promise<Workspace[]> {
  const data = await request<{ workspaces: Workspace[] }>("/api/v1/workspaces");
  return data.workspaces;
}

export async function createWorkspace(name: string): Promise<Workspace> {
  const response = await fetch(`${API_BASE}/api/v1/workspaces`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ name }),
  });
  if (!response.ok) throw new Error(`Could not create workspace: ${response.status}`);
  return response.json() as Promise<Workspace>;
}

export async function renameWorkspace(workspaceId: string, name: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/v1/workspaces/${encodeURIComponent(workspaceId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ name }),
  });
  if (!response.ok) throw new Error(`Could not rename workspace: ${response.status}`);
}

export async function switchWorkspace(workspaceId: string): Promise<void> {
  const response = await fetch(
    `${API_BASE}/api/v1/workspaces/${encodeURIComponent(workspaceId)}/activate`,
    { method: "POST", credentials: "include" },
  );
  if (!response.ok) throw new Error(`Could not switch workspace: ${response.status}`);
}

export async function deleteWorkspace(workspaceId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/v1/workspaces/${encodeURIComponent(workspaceId)}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail ?? `Delete failed: ${response.status}`);
  }
}

export async function deleteResume(): Promise<void> {
  const response = await fetch(`${API_BASE}/api/v1/profile/resume`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok) throw new Error(`Could not delete resume: ${response.status}`);
}

export async function deleteProfile(): Promise<void> {
  const response = await fetch(`${API_BASE}/api/v1/profile`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!response.ok) throw new Error(`Could not delete profile: ${response.status}`);
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
