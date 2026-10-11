import type { SessionView } from "@/features/sessions/state/session-view";
import type { WorkflowState } from "@/lib/workflow";

/**
 * Which session steps are finished, read from persisted workflow state. The
 * step rail ticks a step only on this evidence: a transcript that exists, an
 * attested review, extracted features, a signed report.
 */
export function sessionCompletion(state: WorkflowState): Record<SessionView, boolean> {
  return {
    intake: state.transcriptReady,
    transcript: state.transcriptAttested && state.transcriptReviewStatus === "reviewed",
    findings: state.featuresExtracted,
    report: state.reportStatus === "finalized",
  };
}
