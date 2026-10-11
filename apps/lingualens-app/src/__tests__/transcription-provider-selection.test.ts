import { afterEach, describe, expect, it, vi } from "vitest";

import { findAvailableTranscriptionProvider, transcriptionWaitBudgetMs } from "@/lib/workflow";

function stubProviders(body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } }))
  );
}

describe("transcription provider selection", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("uses local Whisper when the backend reports it available", async () => {
    stubProviders([
      { provider_id: "mock", available: true },
      { provider_id: "local_whisper", available: true }
    ]);

    await expect(findAvailableTranscriptionProvider()).resolves.toBe("local_whisper");
  });

  it("never selects the synthetic mock provider when Whisper is unavailable", async () => {
    stubProviders([
      { provider_id: "mock", available: true },
      { provider_id: "manual", available: true },
      { provider_id: "local_whisper", available: false }
    ]);

    await expect(findAvailableTranscriptionProvider()).resolves.toBeNull();
  });

  it("treats an unexpected response as no provider", async () => {
    stubProviders({});

    await expect(findAvailableTranscriptionProvider()).resolves.toBeNull();
  });

  it("waits longer for longer recordings, within fixed bounds", () => {
    expect(transcriptionWaitBudgetMs(10)).toBe(180_000);
    expect(transcriptionWaitBudgetMs(120)).toBe(840_000);
    expect(transcriptionWaitBudgetMs(3600)).toBe(1_200_000);
    expect(transcriptionWaitBudgetMs(Number.NaN)).toBe(180_000);
  });
});
