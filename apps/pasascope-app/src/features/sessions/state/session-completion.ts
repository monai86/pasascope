import type { SessionView } from "@/features/sessions/state/session-view";
import type { WorkflowState } from "@/lib/workflow";

/**
 * Which session steps are finished, read from persisted workflow state. The
 * step rail ticks a step only on this evidence: a transcript that exists, an
 * attested review, extracted features, a signed report.
 *
 * Later evidence implies earlier steps, because the backend enforces the
 * order: a transcript cannot be attested unless it exists, and a current
 * report draft cannot exist without extracted features. That keeps the rail
 * consistent on views that load only part of the state, such as Report.
 */
export function sessionCompletion(state: WorkflowState, openGates = false): Record<SessionView, boolean> {
  const attested = state.transcriptAttested && state.transcriptReviewStatus === "reviewed";
  const currentReport =
    state.reportStatus === "draft" || state.reportStatus === "reviewed" || state.reportStatus === "finalized";
  // Findings invalidated by a newer transcript are not a finished step.
  const findingsCurrent = state.analysisStatus !== "stale";

  return {
    intake: state.transcriptReady || attested || Boolean(state.backendTranscriptId),
    // With open gates there is no attestation step: the transcript is done once it has been analysed.
    transcript: attested || (openGates && state.featuresExtracted),
    findings: findingsCurrent && (state.featuresExtracted || currentReport),
    // With open gates a saved draft is the finished report; sign-off is optional.
    report: state.reportStatus === "finalized" || (openGates && currentReport),
  };
}
