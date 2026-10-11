import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { EvidenceReviewSection } from "@/features/sessions/findings/evidence-review-section";
import type { WorkflowState } from "@/lib/workflow";

const lines = [
  { lineId: "utt_1", speaker: "INV", text: "เล่นรถไหมครับ" },
  { lineId: "utt_2", speaker: "CHI", text: "เล่นรถไหมครับ" },
] as WorkflowState["transcriptLines"];

function support(reviewStatus: "unreviewed" | "acknowledged" | "dismissed") {
  return {
    resultId: "mlr_1",
    status: "completed",
    providerName: "RuleBasedReviewCueProvider",
    providerVersion: "0.9.1",
    featureSchemaVersion: "features-basic-v1",
    generatedAt: "2026-10-11T00:00:00Z",
    cues: [
      {
        cueCode: "echolalia_review_cue",
        title: "Possible echoed-language cue",
        severity: "review",
        explanation: "A transparent transcript heuristic produced one or more review cues.",
        supportingFeatures: { echolalia_cue_count: 1 },
        evidence: [{ adultUtteranceId: "utt_1", childUtteranceId: "utt_2", category: "immediate_verbatim" }],
        limitations: ["This heuristic may miss relevant context or flag non-clinical patterns."],
        recommendedNextReviewStep: "Verify each possible echo directly in the reviewed transcript.",
        reviewStatus,
      },
    ],
    profileEvidence: [],
    warnings: [],
    limitations: [],
  } as unknown as NonNullable<WorkflowState["mlDecisionSupport"]>;
}

function renderSection(reviewStatus: "unreviewed" | "acknowledged" | "dismissed", onCueReview = vi.fn()) {
  render(
    <EvidenceReviewSection
      mlDecisionSupport={support(reviewStatus)}
      recommendedReviewPoints={[]}
      busy={false}
      onProfileEvidenceReview={vi.fn()}
      onCueReview={onCueReview}
      transcriptLines={lines}
      transcriptHref="/sessions/s1?view=transcript"
    />
  );
  return onCueReview;
}

describe("review cue evidence", () => {
  it("shows the adult and child lines the cue came from", () => {
    renderSection("unreviewed");

    const evidence = screen.getByTestId("cue-evidence-echolalia_review_cue");
    expect(evidence).toHaveTextContent("Adult: เล่นรถไหมครับ");
    expect(evidence).toHaveTextContent("Child: เล่นรถไหมครับ");
    expect(evidence).toHaveTextContent("Repeats the adult turn");
    expect(screen.getByRole("link", { name: "Open transcript" })).toHaveAttribute("href", "/sessions/s1?view=transcript");
  });

  it("lets the therapist confirm or dismiss a cue", () => {
    const onCueReview = renderSection("unreviewed");

    fireEvent.click(screen.getByRole("button", { name: "Confirm after checking" }));
    fireEvent.click(screen.getByRole("button", { name: /Dismiss/ }));

    expect(onCueReview).toHaveBeenNthCalledWith(1, "echolalia_review_cue", "acknowledged");
    expect(onCueReview).toHaveBeenNthCalledWith(2, "echolalia_review_cue", "dismissed");
  });

  it("shows the recorded decision instead of the buttons", () => {
    renderSection("dismissed");

    expect(screen.getByTestId("cue-status-echolalia_review_cue")).toHaveTextContent("Dismissed by therapist");
    expect(screen.queryByRole("button", { name: "Confirm after checking" })).not.toBeInTheDocument();
  });
});
