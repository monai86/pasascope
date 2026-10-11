import { describe, expect, it } from "vitest";

import { sessionCompletion } from "@/features/sessions/state/session-completion";
import { createInitialWorkflowState, type WorkflowState } from "@/lib/workflow";

function state(overrides: Partial<WorkflowState>): WorkflowState {
  return { ...createInitialWorkflowState(), ...overrides };
}

describe("session step completion", () => {
  it("ticks nothing for a new session", () => {
    expect(sessionCompletion(state({}))).toEqual({ intake: false, transcript: false, findings: false, report: false });
  });

  it("does not treat a saved but unattested transcript as a finished review", () => {
    expect(sessionCompletion(state({ transcriptReady: true, transcriptReviewStatus: "in_review" }))).toMatchObject({
      intake: true,
      transcript: false,
      findings: false,
    });
  });

  it("requires both the attestation and the reviewed status", () => {
    expect(sessionCompletion(state({ transcriptAttested: true, transcriptReviewStatus: "in_review" })).transcript).toBe(false);
    expect(sessionCompletion(state({ transcriptAttested: true, transcriptReviewStatus: "reviewed" })).transcript).toBe(true);
  });

  it("keeps the rail consistent when a view loads only the later evidence", () => {
    // The Report view loads the report and attestation, not the intake flags.
    const completion = sessionCompletion(state({
      transcriptAttested: true,
      transcriptReviewStatus: "reviewed",
      reportStatus: "draft",
    }));

    expect(completion).toEqual({ intake: true, transcript: true, findings: true, report: false });
  });

  it("does not count findings a newer transcript has invalidated", () => {
    const completion = sessionCompletion(state({
      transcriptAttested: true,
      transcriptReviewStatus: "reviewed",
      featuresExtracted: true,
      analysisStatus: "stale",
      reportStatus: "stale",
    }));

    expect(completion.findings).toBe(false);
    expect(completion.report).toBe(false);
  });

  it("ticks the report only once it is signed", () => {
    expect(sessionCompletion(state({ reportStatus: "reviewed" })).report).toBe(false);
    expect(sessionCompletion(state({ reportStatus: "finalized" })).report).toBe(true);
  });
});
