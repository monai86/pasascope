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

  it("uses the hosted service when it is the one switched on", async () => {
    stubProviders([
      { provider_id: "mock", available: true },
      { provider_id: "local_whisper", available: false },
      { provider_id: "hosted_whisper", available: true }
    ]);

    await expect(findAvailableTranscriptionProvider()).resolves.toBe("hosted_whisper");
  });

  it("prefers on-device Whisper over the hosted service", async () => {
    stubProviders([
      { provider_id: "hosted_whisper", available: true },
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

describe("review provider selection", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function stubReadiness(byProvider: Record<string, { ready: boolean; reason_codes: string[] }>) {
    const requested: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        requested.push(url);
        const provider = new URL(url).searchParams.get("provider_id") ?? "rule_based_review_cue";
        return new Response(
          JSON.stringify({ provider_id: provider, reasons: [], ...byProvider[provider] }),
          { status: 200, headers: { "content-type": "application/json" } }
        );
      })
    );
    return requested;
  }

  it("uses rule-based review cues when reference evidence is not installed", async () => {
    const { getMlReadiness } = await import("@/services/adapters/analysis-adapter");
    stubReadiness({
      reference_evidence_review: { ready: false, reason_codes: ["ml_provider_unavailable"] },
      rule_based_review_cue: { ready: true, reason_codes: [] },
    });

    await expect(getMlReadiness("TR-1")).resolves.toMatchObject({ ready: true, providerId: "rule_based_review_cue" });
  });

  it("keeps a reference-evidence block that the therapist can resolve", async () => {
    const { getMlReadiness } = await import("@/services/adapters/analysis-adapter");
    const requested = stubReadiness({
      reference_evidence_review: { ready: false, reason_codes: ["features_not_completed"] },
    });

    await expect(getMlReadiness("TR-1")).resolves.toMatchObject({ ready: false, providerId: "reference_evidence_review" });
    expect(requested).toHaveLength(1);
  });
});
