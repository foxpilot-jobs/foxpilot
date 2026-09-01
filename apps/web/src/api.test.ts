import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getActiveJob } from "./api";

describe("getActiveJob API helper", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("handles HTTP 200 with JSON null when no job is active", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => null,
    } as Response);

    const result = await getActiveJob("matching");
    expect(result).toBeNull();
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/v1/profile/jobs/active/matching", {
      credentials: "include",
    });
  });

  it("handles HTTP 200 with a valid active job object", async () => {
    const mockJob = {
      job_id: "active-123",
      kind: "matching",
      status: "running",
    };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockJob,
    } as Response);

    const result = await getActiveJob("matching");
    expect(result).toEqual(mockJob);
  });

  it("maintains backward compatibility with HTTP 404 returning null", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
    } as Response);

    const result = await getActiveJob("matching");
    expect(result).toBeNull();
  });

  it("throws error for other non-OK HTTP status codes", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
    } as Response);

    await expect(getActiveJob("matching")).rejects.toThrow(
      "Unable to check active job status: 500",
    );
  });
});
