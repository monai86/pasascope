"use client";

import { useState } from "react";
import { AlertTriangle, AudioLines, Check, CheckCircle2, FileText } from "lucide-react";

import { AudioReviewWorkbench } from "@/components/audio-review/audio-review-workbench";
import { SafetyNotice } from "@/components/safety-notice";
import { TranscriptEditorPanel } from "@/components/transcript-editor-panel";
import { Button } from "@/components/ui/button";
import { SegmentedControl } from "@/components/ui/segmented-control";
import { SessionContextHeader, type SessionContext } from "@/features/sessions/components/session-context-header";
import { SessionGuide, type SessionGuideAction } from "@/features/sessions/components/session-guide";
import { resolveSessionHref } from "@/features/sessions/state/session-view";
import { EXTRACT_FEATURES_ACTION, GENERATE_REPORT_ACTION } from "@/lib/workflow-glossary";
import type { TranscriptLine, WorkflowState } from "@/lib/workflow";

export type SessionTranscriptViewProps = {
  sessionContext: SessionContext;
  state: WorkflowState;
  lines: TranscriptLine[];
  busy: boolean;
  onLinesChange: (lines: TranscriptLine[]) => void;
  onSaveDraft: () => void;
  onRunQa: () => void;
  onAttest: () => void;
  onExtractFeatures: () => void;
  onGenerateReport: () => void;
  onExport: () => void;
  backendUnavailable?: boolean;
  audioUrl?: string;
};

export function SessionTranscriptView({
  sessionContext,
  state,
  lines,
  busy,
  onLinesChange,
  onSaveDraft,
  onRunQa,
  onAttest,
  onExtractFeatures,
  onGenerateReport,
  onExport,
  backendUnavailable,
  audioUrl,
}: SessionTranscriptViewProps) {
  const reviewChecklist = [
    { label: "Draft saved", complete: state.transcriptSaveStatus === "saved" },
    { label: "QA completed", complete: state.qaStatus !== "not_run" && state.qaStatus !== "fail" },
    { label: "Therapist attested", complete: state.transcriptAttested },
    { label: "Features extracted", complete: state.featuresExtracted },
  ];
  const reportBlockedReason = getReviewReportBlockedReason(state);
  const [reviewMode, setReviewMode] = useState<"audio" | "classic">(audioUrl ? "audio" : "classic");
  const guide = getTranscriptGuide(state, {
    busy,
    findingsHref: resolveSessionHref("findings", sessionContext.sessionId),
    onAttest,
    onExtractFeatures,
  });

  return (
    <div className="mx-auto w-full max-w-7xl space-y-3 sm:space-y-5">
      <SessionContextHeader
        density="compact"
        title="Review Transcript"
        description="Confirm speaker labels and transcript quality before report generation."
        context={sessionContext}
      />
      <SessionGuide
        testId="transcript-guide"
        prompt={guide.prompt}
        primaryAction={guide.primaryAction}
        quickReplies={state.featuresExtracted ? [{ label: "Go to report", href: resolveSessionHref("report", sessionContext.sessionId) }] : []}
      />
      <WorkflowStatus state={state} backendUnavailable={backendUnavailable} />
      {state.transcriptDraftLabel ? (
        <div className="rounded-card border border-[color:var(--color-warning-border)] bg-[color:var(--color-warning-bg)] p-4 text-[color:var(--color-warning-text)]">
          <p className="font-bold">{state.transcriptDraftLabel}</p>
          <p className="mt-1 text-sm">Experimental ASR can be inaccurate. Verify wording, timestamps, and speaker labels before attestation.</p>
        </div>
      ) : null}
      {state.chatWarnings && state.chatWarnings.length > 0 ? (
        <div className="rounded-card border border-[color:var(--color-warning-border)] bg-[color:var(--color-warning-bg)] p-4 text-[color:var(--color-warning-text)]" role="status">
          <p className="font-bold">Import Warnings</p>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
            {state.chatWarnings.map((warning) => <li key={warning}>{warning}</li>)}
          </ul>
        </div>
      ) : null}
      <div className="space-y-5">
        <section className="min-w-0 space-y-4">
          {audioUrl && (
            <SegmentedControl
              label="Transcript review mode"
              value={reviewMode}
              onChange={setReviewMode}
              options={[
                { value: "audio", label: "Audio & Diarization Workbench", icon: AudioLines },
                { value: "classic", label: "Classic Text Editor", icon: FileText },
              ]}
            />
          )}

          {audioUrl && reviewMode === "audio" ? (
            <>
              <AudioReviewWorkbench
                lines={lines}
                onLinesChange={onLinesChange}
                audioUrl={audioUrl}
                sessionId={sessionContext.sessionId}
                isAttested={state.transcriptAttested}
                onAttest={onAttest}
                onSaveDraft={onSaveDraft}
                isBusy={busy}
                findingsStale={Boolean(state.featuresExtracted && state.transcriptSaveStatus === "unsaved")}
              />
              {/* Saving, QA and attestation live in the text editor; point to them from here. */}
              <div className="flex flex-col gap-3 rounded-panel border border-line bg-surface p-4 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm text-ink-muted">
                  {state.transcriptAttested
                    ? "This transcript is attested."
                    : "When the speakers and wording are correct, save the transcript, run QA and attest it."}
                </p>
                <Button variant="secondary" data-testid="continue-to-attestation-button" onClick={() => setReviewMode("classic")} className="shrink-0">
                  Continue to save, QA and attestation
                </Button>
              </div>
            </>
          ) : (
            <TranscriptEditorPanel
              lines={lines}
              qaStatus={state.qaStatus}
              qaIssues={state.qaIssues}
              attested={state.transcriptAttested}
              busy={busy}
              saveStatus={state.transcriptSaveStatus}
              onChange={onLinesChange}
              onSaveDraft={onSaveDraft}
              backendUnavailable={backendUnavailable}
              onRunQa={onRunQa}
              onAttest={onAttest}
              onExport={onExport}
              audioUrl={audioUrl}
            />
          )}
        </section>
        <details className="responsive-details rounded-panel border border-line bg-surface" data-testid="mobile-transcript-report-readiness">
          <summary className="flex min-h-11 cursor-pointer items-center justify-between gap-3 px-4 py-3 text-sm font-semibold text-ink">
            <span>Report readiness</span>
            <span className={reportBlockedReason ? "text-[color:var(--color-warning-text)]" : "text-brand-strong"}>{reportBlockedReason ? "Locked" : "Ready"}</span>
          </summary>
          <section className="border-t border-line p-4 md:border-t-0" aria-label="Report generation readiness">
            <div className="flex items-start gap-2">
              {reportBlockedReason
                ? <AlertTriangle size={18} aria-hidden="true" className="mt-0.5 shrink-0 text-[color:var(--color-warning-text)]" />
                : <CheckCircle2 size={18} aria-hidden="true" className="mt-0.5 shrink-0 text-brand" />}
              <div className="min-w-0">
                <h3 className="font-semibold text-ink">{reportBlockedReason ? "Report generation is locked" : "Ready to generate report"}</h3>
                <p id="generate-report-blocked-reason" className="mt-1 text-sm font-medium text-ink-muted" role={reportBlockedReason ? "status" : undefined}>
                  {reportBlockedReason ?? "Transcript review is complete. Generate the therapist-editable draft report."}
                </p>
              </div>
            </div>
            <ul className="mt-4 grid gap-2 text-sm sm:grid-cols-2 xl:grid-cols-4">
              {reviewChecklist.map((item) => (
                <li key={item.label} className="flex items-center gap-2 rounded-control border border-line bg-surface-soft px-3 py-2 font-medium text-ink">
                  <span
                    aria-hidden="true"
                    className={`grid h-5 w-5 shrink-0 place-items-center rounded-full ${item.complete ? "bg-brand text-white" : "border border-line-strong bg-surface text-ink-subtle"}`}
                  >
                    {item.complete ? <Check size={12} strokeWidth={3} /> : null}
                  </span>
                  <span>{item.label}</span>
                  <span className="sr-only">{item.complete ? "(done)" : "(not done)"}</span>
                </li>
              ))}
            </ul>
            <Button
              variant="secondary"
              className="mt-4 w-full"
              onClick={onGenerateReport}
              disabled={busy || Boolean(reportBlockedReason)}
              aria-describedby={reportBlockedReason ? "generate-report-blocked-reason" : undefined}
              title={reportBlockedReason}
            >
              {GENERATE_REPORT_ACTION}
            </Button>
          </section>
        </details>
        <details className="responsive-details rounded-panel border border-line bg-surface" data-testid="mobile-transcript-review-requirements">
          <summary className="flex min-h-11 cursor-pointer items-center justify-between px-4 py-3 text-sm font-semibold text-ink">
            <span>Review requirements</span>
            <span aria-hidden="true">›</span>
          </summary>
          <div className="border-t border-line md:border-t-0">
            <SafetyNotice>
              Report generation requires a saved draft, completed QA, therapist attestation, and extracted language-sample features. Editing after attestation resets these gates.
            </SafetyNotice>
          </div>
        </details>
      </div>
    </div>
  );
}

/**
 * The one thing to do next on this page. Saving and QA are done with the
 * editor's own controls, so for those the guide only says so; attesting,
 * extracting features and moving on are offered here as the single primary
 * action, in that order.
 */
function getTranscriptGuide(
  state: WorkflowState,
  actions: { busy: boolean; findingsHref: string; onAttest: () => void; onExtractFeatures: () => void },
): { prompt: string; primaryAction?: SessionGuideAction } {
  // Attestation is the server's record that the saved transcript was reviewed,
  // and any later edit clears it, so an attested transcript needs no re-check
  // of the save and QA steps here.
  const attested = state.transcriptAttested && state.transcriptReviewStatus === "reviewed";

  if (attested && state.featuresExtracted) {
    return {
      prompt: "Features are extracted from the attested transcript. Review them in Findings.",
      primaryAction: { label: "Continue to Findings", href: actions.findingsHref },
    };
  }
  if (attested) {
    return {
      prompt: "The transcript is reviewed and attested. Next, we'll extract the language-sample features.",
      primaryAction: state.backendTranscriptId
        ? {
            label: actions.busy ? "Extracting..." : EXTRACT_FEATURES_ACTION,
            onClick: actions.onExtractFeatures,
            disabled: actions.busy,
            testId: "extract-features-button",
          }
        : undefined,
    };
  }
  if (state.transcriptSaveStatus !== "saved") {
    return { prompt: "Check the speaker labels and wording below, then save the draft." };
  }
  if (state.qaStatus === "not_run") {
    return { prompt: "The draft is saved. Run QA on the transcript before attesting it." };
  }
  if (state.qaStatus === "fail") {
    return { prompt: "QA found issues that block attestation. Fix them, save, and run QA again." };
  }
  return {
    prompt: "The draft is saved and QA is complete. Attest the transcript to confirm your review.",
    primaryAction: state.backendTranscriptId
      ? { label: actions.busy ? "Recording attestation..." : "Attest this transcript", onClick: actions.onAttest, disabled: actions.busy }
      : undefined,
  };
}

function getReviewReportBlockedReason(state: WorkflowState) {
  if (state.transcriptSaveStatus !== "saved") return "Save the transcript draft before generating a report.";
  if (state.qaStatus === "not_run") return "Run transcript QA before generating a report.";
  if (state.qaStatus === "fail") return "Resolve transcript QA issues before generating a report.";
  if (state.error && state.statusMessage === "Attestation failed.") {
    return "Attestation did not finish. Try Attest transcript again before generating a report.";
  }
  if (!state.transcriptAttested || state.transcriptReviewStatus !== "reviewed") {
    return "Click Attest transcript before generating a report.";
  }
  if (!state.featuresExtracted) return "Extract language-sample features before generating a report.";
  return undefined;
}

function WorkflowStatus({ state, backendUnavailable }: { state: WorkflowState; backendUnavailable?: boolean }) {
  if (!state.statusMessage && !state.error) return null;
  const isError = Boolean(state.error);
  const routineSaveAnnouncement = !isError && (
    state.statusMessage === "Unsaved transcript edits."
    || state.statusMessage === "Transcript draft saved."
  );
  if (routineSaveAnnouncement) return null;
  if (state.statusMessage && !isError && backendUnavailable) return null;
  const className = isError
    ? "rounded-card border border-[color:var(--color-danger-border)] bg-[color:var(--color-danger-bg)] p-3 text-sm text-[color:var(--color-danger-text)] animate-fade-in sm:p-4"
    : "rounded-card border border-[color:var(--color-info-border)] bg-[color:var(--color-info-bg)] p-3 text-sm text-[color:var(--color-info-text)] animate-fade-in sm:p-4";
  return (
    <div className={className} role={isError ? "alert" : "status"} aria-live="polite">
      {state.statusMessage ? <p className="font-semibold">{state.statusMessage}</p> : null}
      {state.error ? <p className="mt-1 font-semibold">{state.error}</p> : null}
    </div>
  );
}
