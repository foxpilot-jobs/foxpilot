import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../../../api";
import { ProfileSetupPage } from "./ProfileSetupPage";

vi.mock("../../../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../api")>();
  return {
    ...actual,
    getProfile: vi.fn(),
    getActiveJob: vi.fn(),
    getBackgroundJob: vi.fn(),
    runMatching: vi.fn(),
    uploadResume: vi.fn(),
    deleteResume: vi.fn(),
    deleteProfile: vi.fn(),
  };
});

describe("ProfileSetupPage Matching Status Lifecycle & Regression Tests", () => {
  const mockProfile: api.Profile = {
    resume_filename: "resume.pdf",
    profile: { summary: "Software Engineer", target_roles: ["Backend Engineer"] },
    created_at: "2026-08-31T10:00:00Z",
    updated_at: "2026-08-31T10:00:00Z",
  };

  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(api.getProfile).mockResolvedValue(mockProfile);
    vi.mocked(api.getActiveJob).mockResolvedValue(null);
  });

  it("1. renders idle UI when no active job exists on page load and does NOT trigger matching automatically", async () => {
    vi.mocked(api.getActiveJob).mockResolvedValue(null);

    render(
      <MemoryRouter>
        <ProfileSetupPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /run matching/i })).toBeInTheDocument();
    });

    expect(screen.queryByText(/matching queued/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/matching in progress/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /run matching/i })).not.toBeDisabled();
    expect(api.runMatching).not.toHaveBeenCalled();
  });

  it("2. shows queued UI when an active queued job exists on page load", async () => {
    const queuedJob: api.BackgroundJob = {
      job_id: "job-queued-1",
      kind: "matching",
      status: "queued",
      result: null,
      error: null,
      created_at: "2026-08-31T10:00:00Z",
      updated_at: "2026-08-31T10:00:00Z",
    };

    vi.mocked(api.getActiveJob).mockResolvedValue(queuedJob);
    vi.mocked(api.getBackgroundJob).mockResolvedValue(queuedJob);

    render(
      <MemoryRouter>
        <ProfileSetupPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText(/matching queued…/i)).toBeInTheDocument();
    });

    expect(
      screen.getByText(/foxpilot is preparing to compare roles against your profile/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /run matching/i })).toBeDisabled();
    expect(api.runMatching).not.toHaveBeenCalled();
  });

  it("3. shows running UI when an active running job exists on page load", async () => {
    const runningJob: api.BackgroundJob = {
      job_id: "job-running-1",
      kind: "matching",
      status: "running",
      result: null,
      error: null,
      created_at: "2026-08-31T10:00:00Z",
      updated_at: "2026-08-31T10:00:00Z",
    };

    vi.mocked(api.getActiveJob).mockResolvedValue(runningJob);
    vi.mocked(api.getBackgroundJob).mockResolvedValue(runningJob);

    render(
      <MemoryRouter>
        <ProfileSetupPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText(/matching in progress…/i)).toBeInTheDocument();
    });

    expect(
      screen.getByText(/foxpilot is comparing roles against your profile/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /run matching/i })).toBeDisabled();
  });

  it("4. clears status card and spinner immediately when job reaches completed state", async () => {
    const runningJob: api.BackgroundJob = {
      job_id: "job-100",
      kind: "matching",
      status: "running",
      result: null,
      error: null,
      created_at: "2026-08-31T10:00:00Z",
      updated_at: "2026-08-31T10:00:00Z",
    };
    const completedJob: api.BackgroundJob = {
      ...runningJob,
      status: "completed",
      result: { analyzed: 12, skipped: 33, failed: 0 },
    };

    vi.mocked(api.getActiveJob).mockResolvedValue(runningJob);
    vi.mocked(api.getBackgroundJob)
      .mockResolvedValueOnce(runningJob)
      .mockResolvedValueOnce(completedJob);

    render(
      <MemoryRouter>
        <ProfileSetupPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText(/12 new matches found/i)).toBeInTheDocument();
    });

    expect(screen.getByRole("link", { name: /view matches/i })).toHaveAttribute(
      "href",
      "/app/matches",
    );
    expect(screen.queryByText(/matching in progress/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /run matching/i })).not.toBeDisabled();
  });

  it("5. clears status card and spinner immediately when job reaches failed state", async () => {
    const runningJob: api.BackgroundJob = {
      job_id: "job-300",
      kind: "matching",
      status: "running",
      result: null,
      error: null,
      created_at: "2026-08-31T10:00:00Z",
      updated_at: "2026-08-31T10:00:00Z",
    };
    const failedJob: api.BackgroundJob = {
      ...runningJob,
      status: "failed",
      error: "LLM Rate Limit Exceeded",
    };

    vi.mocked(api.runMatching).mockResolvedValue(runningJob);
    vi.mocked(api.getBackgroundJob).mockResolvedValue(failedJob);

    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ProfileSetupPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /run matching/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /run matching/i }));

    await waitFor(() => {
      expect(screen.getByText(/matching failed: llm rate limit exceeded/i)).toBeInTheDocument();
    });

    expect(screen.queryByText(/matching in progress/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /run matching/i })).not.toBeDisabled();
  });

  it("6 & 7. user clicking Run matching starts polling and stops on terminal state", async () => {
    const queuedJob: api.BackgroundJob = {
      job_id: "job-200",
      kind: "matching",
      status: "queued",
      result: null,
      error: null,
      created_at: "2026-08-31T10:00:00Z",
      updated_at: "2026-08-31T10:00:00Z",
    };
    const completedZeroJob: api.BackgroundJob = {
      ...queuedJob,
      status: "completed",
      result: { analyzed: 0, skipped: 45, failed: 0 },
    };

    vi.mocked(api.runMatching).mockResolvedValue(queuedJob);
    vi.mocked(api.getBackgroundJob).mockResolvedValue(completedZeroJob);

    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ProfileSetupPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /run matching/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /run matching/i }));
    expect(api.runMatching).toHaveBeenCalledOnce();

    await waitFor(() => {
      expect(
        screen.getByText(/no new matches found. your existing matches are up to date/i),
      ).toBeInTheDocument();
    });

    expect(screen.queryByRole("link", { name: /view matches/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /run matching/i })).not.toBeDisabled();
  });

  it("8. page reload does NOT create a new matching job", async () => {
    vi.mocked(api.getActiveJob).mockResolvedValue(null);

    const { unmount } = render(
      <MemoryRouter>
        <ProfileSetupPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /run matching/i })).toBeInTheDocument();
    });

    unmount();

    render(
      <MemoryRouter>
        <ProfileSetupPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /run matching/i })).toBeInTheDocument();
    });

    expect(api.runMatching).not.toHaveBeenCalled();
  });

  it("keeps long-running job active with progress and long-running hint without throwing a timeout error", async () => {
    const oldDate = new Date(Date.now() - 5 * 60 * 1000).toISOString();
    const longRunningJob: api.BackgroundJob = {
      job_id: "job-long-1",
      kind: "matching",
      status: "running",
      progress: { processed: 45, total: 100 },
      result: null,
      error: null,
      created_at: oldDate,
      updated_at: oldDate,
    };

    vi.mocked(api.getActiveJob).mockResolvedValue(longRunningJob);
    vi.mocked(api.getBackgroundJob).mockResolvedValue(longRunningJob);

    render(
      <MemoryRouter>
        <ProfileSetupPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(
        screen.getByText(
          /foxpilot is comparing roles against your profile \(45 of 100 candidates processed\)/i,
        ),
      ).toBeInTheDocument();
    });

    expect(screen.getByText(/matching is taking a little longer/i)).toBeInTheDocument();
    expect(
      screen.queryByText(/processing is taking longer than expected/i),
    ).not.toBeInTheDocument();
  });

  it("upload success triggers profile refetch and updates UI without full page refresh", async () => {
    const emptyProfile: api.Profile = {
      resume_filename: "",
      profile: {},
      created_at: null,
      updated_at: null,
    };
    const extractedProfile: api.Profile = {
      resume_filename: "uploaded_resume.pdf",
      profile: {
        summary: "Operations Manager with 6 years experience.",
        target_roles: ["Operations Manager"],
        skills: ["Inventory Management", "Logistics"],
      },
      created_at: "2026-09-05T10:00:00Z",
      updated_at: "2026-09-05T10:00:00Z",
    };
    const uploadJob: api.BackgroundJob = {
      job_id: "upload-job-1",
      kind: "profile_generation",
      status: "queued",
      result: null,
      error: null,
      created_at: "2026-09-05T10:00:00Z",
      updated_at: "2026-09-05T10:00:00Z",
    };
    const completedJob: api.BackgroundJob = {
      ...uploadJob,
      status: "completed",
    };

    vi.mocked(api.getProfile)
      .mockResolvedValueOnce(emptyProfile)
      .mockResolvedValueOnce({ ...emptyProfile, resume_filename: "uploaded_resume.pdf" })
      .mockResolvedValueOnce(extractedProfile);

    vi.mocked(api.uploadResume).mockResolvedValue(uploadJob);
    vi.mocked(api.getBackgroundJob)
      .mockResolvedValueOnce(uploadJob)
      .mockResolvedValueOnce(completedJob);

    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ProfileSetupPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText(/no resume uploaded yet/i)).toBeInTheDocument();
    });

    const file = new File(["dummy pdf content"], "uploaded_resume.pdf", {
      type: "application/pdf",
    });
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput).not.toBeNull();

    await user.upload(fileInput, file);

    await waitFor(() => {
      expect(api.uploadResume).toHaveBeenCalledOnce();
    });

    await waitFor(() => {
      expect(screen.getByText(/operations manager with 6 years experience/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/inventory management/i)).toBeInTheDocument();
    expect(screen.getAllByText(/uploaded_resume.pdf/i).length).toBeGreaterThan(0);
  });

  it("pending extraction shows analyzing state spinner in ProfileOverview instead of empty fields notice", async () => {
    const pendingJob: api.BackgroundJob = {
      job_id: "job-pending-1",
      kind: "profile_generation",
      status: "running",
      result: null,
      error: null,
      created_at: "2026-09-05T10:00:00Z",
      updated_at: "2026-09-05T10:00:00Z",
    };

    vi.mocked(api.getActiveJob).mockResolvedValue(pendingJob);
    vi.mocked(api.getBackgroundJob).mockResolvedValue(pendingJob);
    vi.mocked(api.getProfile).mockResolvedValue({
      resume_filename: "my_resume.pdf",
      profile: {},
      created_at: "2026-09-05T10:00:00Z",
      updated_at: "2026-09-05T10:00:00Z",
    });

    render(
      <MemoryRouter>
        <ProfileSetupPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(
        screen.getByText(/analyzing your resume\.\.\. foxpilot is extracting your skills/i),
      ).toBeInTheDocument();
    });

    expect(
      screen.queryByText(/your profile was extracted, but no structured fields were found/i),
    ).not.toBeInTheDocument();
  });

  it("extraction failure displays a clear error alert", async () => {
    const runningProfileJob: api.BackgroundJob = {
      job_id: "job-failed-1",
      kind: "profile_generation",
      status: "running",
      result: null,
      error: null,
      created_at: "2026-09-05T10:00:00Z",
      updated_at: "2026-09-05T10:00:00Z",
    };
    const failedProfileJob: api.BackgroundJob = {
      ...runningProfileJob,
      status: "failed",
      error: "Corrupted PDF structure",
    };

    vi.mocked(api.getActiveJob).mockResolvedValue(runningProfileJob);
    vi.mocked(api.getBackgroundJob)
      .mockResolvedValueOnce(runningProfileJob)
      .mockResolvedValueOnce(failedProfileJob);

    render(
      <MemoryRouter>
        <ProfileSetupPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(
        screen.getByText(/resume analysis failed: corrupted pdf structure/i),
      ).toBeInTheDocument();
    });
  });

  it("extraction completed with empty fields displays empty state notice with re-analyze button", async () => {
    vi.mocked(api.getProfile).mockResolvedValue({
      resume_filename: "empty_resume.pdf",
      profile: {},
      created_at: "2026-09-05T10:00:00Z",
      updated_at: "2026-09-05T10:00:00Z",
    });

    render(
      <MemoryRouter>
        <ProfileSetupPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(
        screen.getByText(/your profile was extracted, but no structured fields were found/i),
      ).toBeInTheDocument();
    });

    expect(screen.getAllByRole("button", { name: /re-analyze resume/i }).length).toBeGreaterThan(0);
  });

  it("10. reproduces race condition: job completes, first getProfile returns {}, second getProfile returns structured fields, and UI displays fields without refresh", async () => {
    const emptyProfile: api.Profile = {
      resume_filename: "race_resume.pdf",
      profile: {},
      created_at: "2026-09-05T10:00:00Z",
      updated_at: "2026-09-05T10:00:00Z",
    };
    const structuredProfile: api.Profile = {
      resume_filename: "race_resume.pdf",
      profile: {
        summary: "Senior Systems Engineer with 8 years experience.",
        target_roles: ["Systems Engineer", "DevOps Engineer"],
        skills: ["Kubernetes", "Terraform", "Go"],
      },
      created_at: "2026-09-05T10:00:00Z",
      updated_at: "2026-09-05T10:00:05Z",
    };
    const uploadJob: api.BackgroundJob = {
      job_id: "race-job-1",
      kind: "profile_generation",
      status: "queued",
      result: null,
      error: null,
      created_at: "2026-09-05T10:00:00Z",
      updated_at: "2026-09-05T10:00:00Z",
    };
    const completedJob: api.BackgroundJob = {
      ...uploadJob,
      status: "completed",
    };

    // 1. Initial page load -> empty profile
    // 2. getProfile after upload -> empty profile (transient)
    // 3. getProfile when job status completed detected -> empty profile (transient snapshot)
    // 4. getProfile during finalizing retry loop -> structured profile!
    vi.mocked(api.getProfile)
      .mockResolvedValueOnce(emptyProfile)
      .mockResolvedValueOnce(emptyProfile)
      .mockResolvedValueOnce(emptyProfile)
      .mockResolvedValueOnce(structuredProfile);

    vi.mocked(api.uploadResume).mockResolvedValue(uploadJob);
    vi.mocked(api.getBackgroundJob).mockResolvedValue(completedJob);

    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ProfileSetupPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(
        screen.getByText(/your profile was extracted, but no structured fields were found/i),
      ).toBeInTheDocument();
    });

    const file = new File(["race test pdf"], "race_resume.pdf", { type: "application/pdf" });
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput).not.toBeNull();

    await user.upload(fileInput, file);

    // Verify UI shows finalizing state during transient empty GET responses and does NOT render "no structured fields found"
    await waitFor(() => {
      expect(
        screen.getByText(/senior systems engineer with 8 years experience/i),
      ).toBeInTheDocument();
    });

    expect(screen.getByText(/kubernetes/i)).toBeInTheDocument();
    expect(screen.getByText(/terraform/i)).toBeInTheDocument();
    expect(
      screen.queryByText(/your profile was extracted, but no structured fields were found/i),
    ).not.toBeInTheDocument();
  });
});
