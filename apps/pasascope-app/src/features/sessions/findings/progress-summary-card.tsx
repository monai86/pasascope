"use client";

import type { AiAssistanceArea, AiReview, WorkflowState } from "@/lib/workflow";
import { generateAiReviewBlockedReason } from "@/lib/workflow-gates";
import { useGateReason } from "@/lib/gate-reason";

/**
 * AI-assisted Progress Summary card for the Findings view. Surfaces the same
 * longitudinal context (previous-session deltas plus the typical-development
 * reference band when available) that the printed report and the dashboard
 * chart carry, so the therapist sees it without opening a report. When no
 * AI-assisted review exists yet, it offers generation with an inline
 * workflow-gate reason (aria-describedby) when blocked.
 */
export function ProgressSummaryCard({
  state,
  aiReview,
  busy,
  onGenerateAiReview,
}: {
  state: WorkflowState;
  aiReview?: AiReview;
  busy: boolean;
  onGenerateAiReview: () => void;
}) {
  const progressSummaryArea: AiAssistanceArea | undefined = aiReview?.assistanceAreas.find(
    (area) => area.area === "Progress Summary"
  );
  const gate = useGateReason();
  const aiReviewReason = gate(generateAiReviewBlockedReason(state));

  return (
    <section aria-labelledby="findings-progress-summary-title" className="rounded-shell border border-line bg-surface p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="findings-progress-summary-title" className="text-lg font-semibold text-ink">Progress Summary</h2>
          <p className="mt-1 text-sm leading-6 text-ink-muted">
            AI-assisted longitudinal context for this case, including the typical-development reference band when available.
          </p>
        </div>
        {progressSummaryArea ? (
          <span className="rounded-full bg-surface-muted px-3 py-1 text-xs font-semibold text-ink">
            AI-assisted review
          </span>
        ) : null}
      </div>
      {progressSummaryArea ? (
        <div className="mt-4 space-y-3">
          <p className="rounded-panel border border-line bg-surface px-4 py-3 text-sm leading-6 text-ink">
            {progressSummaryArea.summary}
          </p>
          {progressSummaryArea.contributingFactors.length > 0 ? (
            <ul className="space-y-2 text-sm leading-6 text-ink-muted">
              {progressSummaryArea.contributingFactors.map((factor) => (
                <li key={factor} className="flex gap-2">
                  <span aria-hidden="true" className="text-ink-subtle">•</span>
                  <span>{factor}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : (
        <div className="mt-4">
          <button
            type="button"
            className="flex min-h-11 items-center justify-center rounded-card bg-brand-strong px-4 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
            onClick={() => onGenerateAiReview()}
            disabled={busy || Boolean(aiReviewReason)}
            aria-describedby={aiReviewReason ? "generate-ai-review-reason" : undefined}
            data-testid="generate-ai-review-button"
          >
            {busy ? "Generating..." : "Generate AI-assisted review"}
          </button>
          {aiReviewReason ? (
            <p id="generate-ai-review-reason" role="status" className="mt-2 rounded-card border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] px-3 py-2 text-sm font-semibold text-[color:var(--color-warning-text)]">
              {aiReviewReason}
            </p>
          ) : null}
        </div>
      )}
    </section>
  );
}
