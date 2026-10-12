"use client";
import { useMemo } from "react";
import Link from "next/link";
import { Clipboard, Download, Printer, Send, ShieldCheck } from "lucide-react";
import { SafetyNote, WorkspacePanel } from "@/components/workbench-ui";
import { BackendAvailabilityBanner } from "@/components/backend-availability-banner";
import { SessionContextHeader } from "@/features/sessions/components/session-context-header";
import { sessionCompletion } from "@/features/sessions/state/session-completion";
import { SessionGuide } from "@/features/sessions/components/session-guide";
import { ReportProvenanceItem, reportSectionDefinitions, WorkflowStatus } from "@/features/sessions/report/session-report-components";
import { useSessionReport, type SessionReportViewProps } from "@/features/sessions/report/use-session-report";
import {
  finalizedSafetyLabel,
  finalizedSafetyMetadataString,
  reportGeneratedVersion,
  reportMetadataString,
  reportSaveStateLabel,
  reportSourceLabel,
  reportWorkflowLabel,
  signedSnapshotNumber,
  signedSnapshotProviderString,
  signedSnapshotString,
  versionLabel,
} from "@/features/sessions/report/session-report-model";
import { reportMessages } from "@/features/sessions/report/report.messages";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/i18n/format";
import { useLocale, useMessages } from "@/i18n/locale-provider";
import { useSafetyCopy } from "@/lib/safety-copy";
export function SessionReportView(props: SessionReportViewProps) {
  const identityKey = JSON.stringify([
    props.sessionId ?? "",
    props.caseId ?? "",
    props.transcriptId ?? "",
    props.reportId ?? "",
  ]);
  return <ReportSummaryIdentityScope key={identityKey} {...props} />;
}

function ReportSummaryIdentityScope({ caseId, sessionId, transcriptId, reportId }: SessionReportViewProps) {
  const {
    hasLocator,
    state,
    busy,
    reportText,
    setReportText,
    therapistNotes,
    setTherapistNotes,
    goalsText,
    setGoalsText,
    exportedCha,
    providerId,
    setProviderId,
    allowFallback,
    setAllowFallback,
    backendReport,
    primaryTherapistLabel,
    primaryTherapistAssigned,
    confirmationChecked,
    setConfirmationChecked,
    snapshotIntegrity,
    backendUnavailable,
    isFailedSafety,
    isFinalized,
    isStale,
    isNotStarted,
    isSnapshotIntegrityChecking,
    hasSnapshotIntegrityError,
    signedSnapshotVerified,
    signedActionsBlocked,
    canRenderReportMetadata,
    isEditorLocked,
    transcriptUnlocked,
    identityLoaded,
    persist,
    handleGenerateDraft,
    handleSaveDraft,
    handleExport,
    handleExportCha,
    handleCopyLocalDemoShareLink,
    handleMarkSent,
    handleFinalize,
    handleCreateRevision,
    isFinalizeDisabled,
  } = useSessionReport({ caseId, sessionId, transcriptId, reportId });

  const t = useMessages(reportMessages);
  const { locale } = useLocale();
  const safety = useSafetyCopy();
  const draftState = isSnapshotIntegrityChecking
    ? "verifying"
    : hasSnapshotIntegrityError
      ? "unavailable"
      : isFinalized
        ? "signed"
        : isStale
          ? "stale"
          : isNotStarted
            ? "notStarted"
            : "draft";
  // One action is the next step at any moment: generate a draft, then save
  // edits, then sign off. That one is solid; the others stay outlined.
  const nextAction = isFinalized || isStale
    ? undefined
    : isNotStarted
      ? "generate"
      : state.reportSaveStatus === "unsaved" || state.reportSaveStatus === "failed"
        ? "save"
        : "finalize";

  const reportSections = useMemo(() => reportSectionDefinitions.map((section) => {
    if (section.title !== "Strengths" || !state.featureSummary.length) return section;
    return {
      ...section,
      items: state.featureSummary.map((item) => `${item.label}: ${item.value}`),
    };
  }), [state.featureSummary]);

  return (
    <>
      <BackendAvailabilityBanner unavailable={backendUnavailable} />
      <SessionContextHeader
        title={t.title}
        description={t.description}
        context={{
          sessionId: state.backendSessionId ?? state.sessionId ?? sessionId,
          caseId: state.caseId || caseId,
          caseLabel: state.childName || state.caseInfo.clientLabel || state.caseId || caseId,
          consentStatus: undefined,
          sourceLabel: isFinalized
            ? signedSnapshotVerified
              ? reportSourceLabel(backendReport)
              : undefined
            : reportSourceLabel(backendReport),
          workflowStatus: reportWorkflowLabel(state, backendReport),
          dataMode: state.backendSessionId
            ? "backend"
            : backendUnavailable && hasLocator
              ? "unavailable"
              : "local_draft",
          activeView: "report",
          completion: sessionCompletion(state),
        }}
      />      <SessionGuide
        testId="report-guide"
        prompt={
          isStale
            ? t.guide.stale
            : isFinalized
              ? t.guide.finalized
              : isNotStarted
                ? t.guide.notStarted
                : t.guide.draft
        }
        quickReplies={
          isStale
            ? [
                { label: t.guide.goToFindings, href: state.backendSessionId ? `/sessions/${state.backendSessionId}?view=findings` : "/cases" },
              ]
            : [
                { label: t.guide.goToFindings, href: state.backendSessionId ? `/sessions/${state.backendSessionId}?view=findings` : "/cases" },
                { label: t.guide.reviseTranscript, href: state.backendSessionId ? `/sessions/${state.backendSessionId}?view=transcript` : "/cases" },
              ]
        }
      />
      {/* The draft leads; status, sign-off and metadata sit beside it. */}
      <div className="grid min-w-0 gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(18rem,26rem)]">
      <WorkspacePanel className="min-w-0 p-6">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold text-ink">
              {t.draft.titles[draftState]}
            </h2>
            <p className="mt-2 text-sm leading-6 text-ink-muted">
              {t.draft.notes[draftState]}
            </p>
          </div>
          <button
            className={`min-h-11 shrink-0 rounded-full px-4 py-2 text-sm font-bold disabled:opacity-50 ${nextAction === "generate" ? "bg-brand text-white" : "border border-brand-border bg-surface text-brand"}`}
            onClick={() => handleGenerateDraft(false)}
            disabled={busy || isFinalized || isStale || !transcriptUnlocked}
            data-testid="generate-report-draft-button"
          >
            {busy ? t.draft.working : t.draft.generate}
          </button>
        </div>
        {!transcriptUnlocked ? (
          <p className="mt-4 rounded-card border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] p-3 text-sm font-semibold text-[color:var(--color-warning-text)]">
            {t.draft.attestationRequired}
          </p>
        ) : null}

        {/* Failed Safety Warning Banner */}
        {!isFinalized && isFailedSafety && (
          <div className="mt-4 rounded-panel border border-[color:var(--color-danger-border)] bg-[color:var(--color-danger-bg)] p-5 text-[color:var(--color-danger-text)] animate-fade-in" data-testid="report-safety-failed">
            <h3 className="text-lg font-bold text-[color:var(--color-danger-text)]">{t.safety.failedTitle}</h3>
            <p className="mt-1 text-sm text-[color:var(--color-danger-text)]">
              {t.safety.failedBody}
            </p>
            <ul className="mt-3 space-y-2 text-sm">
              {backendReport?.safety_validation_result?.issues.map((issue: any) => (
                <li key={issue.issue_id} className="flex items-start gap-2 bg-surface-muted p-3 rounded-card border border-[color:var(--color-danger-border)]">
                  <span className="font-bold text-[color:var(--color-danger-text)] uppercase tracking-wide text-xs bg-[color:var(--color-danger-bg)] px-2 py-0.5 rounded shrink-0 mt-0.5">
                    {issue.severity}
                  </span>
                  <div>
                    <p className="font-semibold text-[color:var(--color-danger-text)]">{issue.message}</p>
                    {issue.detected_text && (
                      <p className="mt-1 text-xs text-ink">
                        {t.safety.detected} <code className="bg-[color:var(--color-danger-bg)] px-1 py-0.5 rounded text-[color:var(--color-danger-text)] font-mono">&quot;{issue.detected_text}&quot;</code>
                      </p>
                    )}
                    {issue.suggested_fix && (
                      <p className="mt-1 text-xs text-ink-muted italic">
                        {t.safety.fix} {issue.suggested_fix}
                      </p>
                    )}
                  </div>
                </li>
              ))}
            </ul>
            <button
              onClick={() => handleGenerateDraft(true)}
              className="mt-4 inline-flex min-h-11 items-center justify-center gap-2 rounded-card bg-brand px-5 font-bold text-white hover:bg-brand-strong active:scale-95 transition-transform"
              data-testid="regenerate-safe-template-button"
            >
              {t.safety.regenerateSafe}
            </button>
          </div>
        )}

        {/* Non-blocking Safety Warnings (Yellow Alert) */}
        {!isFinalized && !isFailedSafety && backendReport?.safety_validation_result?.issues && backendReport.safety_validation_result.issues.length > 0 && (
          <div className="mt-4 rounded-panel border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] p-5 text-[color:var(--color-warning-text)] animate-fade-in" data-testid="report-safety-warning">
            <h3 className="text-lg font-bold text-[color:var(--color-warning-text)]">{t.safety.warningsTitle}</h3>
            <p className="mt-1 text-sm text-[color:var(--color-warning-text)]">
              {t.safety.warningsBody}
            </p>
            <ul className="mt-3 space-y-2 text-sm">
              {backendReport.safety_validation_result.issues.map((issue: any) => (
                <li key={issue.issue_id} className="flex items-start gap-2 bg-surface-muted p-3 rounded-card border border-[color:var(--color-attention-border)]">
                  <span className="font-bold text-[color:var(--color-warning-text)] uppercase tracking-wide text-xs bg-[color:var(--color-warning-bg)] px-2 py-0.5 rounded shrink-0 mt-0.5">
                    {issue.severity}
                  </span>
                  <div>
                    <p className="font-semibold text-[color:var(--color-warning-text)]">{issue.message}</p>
                    {issue.detected_text && (
                      <p className="mt-1 text-xs text-ink">
                        {t.safety.detected} <code className="bg-[color:var(--color-warning-bg)] px-1 py-0.5 rounded text-[color:var(--color-warning-text)] font-mono">&quot;{issue.detected_text}&quot;</code>
                      </p>
                    )}
                    {issue.suggested_fix && (
                      <p className="mt-1 text-xs text-ink-muted italic">
                        {t.safety.fix} {issue.suggested_fix}
                      </p>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}

        <textarea className="mt-5 min-h-80 w-full rounded-panel border border-line bg-surface p-4 text-sm leading-6 text-ink outline-none focus:ring-2 focus:ring-brand" value={reportText} readOnly={isEditorLocked || isNotStarted} onChange={(event) => {
          if (isEditorLocked || isNotStarted) return;
          setReportText(event.target.value);
          persist({ ...state, reportMarkdown: event.target.value, reportSaveStatus: "unsaved", statusMessage: "Unsaved report edits.", error: undefined });
        }} aria-label={isStale ? t.draft.editorLabels.stale : isFinalized ? t.draft.editorLabels.signed : isNotStarted ? t.draft.editorLabels.notStarted : t.draft.editorLabels.draft} aria-describedby={isStale ? "stale-report-explanation" : undefined} data-testid="report-preview" />
        <p className="mt-2 text-sm font-semibold text-ink-muted" role="status">
          {state.reportSaveStatus === "saving" ? t.draft.saveStatus.saving : state.reportSaveStatus === "saved" ? t.draft.saveStatus.saved : state.reportSaveStatus === "failed" ? t.draft.saveStatus.failed : state.reportSaveStatus === "unsaved" ? t.draft.saveStatus.unsaved : t.draft.saveStatus.idle}
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            className={`inline-flex min-h-11 items-center gap-2 rounded-full px-5 py-2.5 text-sm font-bold disabled:opacity-50 ${nextAction === "save" ? "bg-brand text-white" : "border border-brand-border bg-surface text-brand"}`}
            onClick={handleSaveDraft}
            disabled={busy || isEditorLocked || !state.reportId || state.reportSaveStatus === "saved"}
            data-testid="save-report-draft-button"
          >
            {t.draft.save}
          </button>
        </div>
        <div className="mt-4 border-t border-line pt-4">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-ink-muted">{t.export.title}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <button className="inline-flex items-center gap-2 rounded-card border border-line bg-surface px-4 py-3 text-sm font-bold text-brand disabled:opacity-50" disabled={!isFinalized || signedActionsBlocked} onClick={() => void handleExport("markdown")}><Download size={18} aria-hidden="true" />{t.export.markdown}</button>
            <button className="inline-flex items-center gap-2 rounded-card border border-line bg-surface px-4 py-3 text-sm font-bold text-brand disabled:opacity-50" disabled={!isFinalized || signedActionsBlocked} onClick={() => void handleExport("html")}><Download size={18} aria-hidden="true" />{t.export.html}</button>
            {isFinalized && state.backendReportId && !signedActionsBlocked ? (
              <Link
                href={`/reports/print?report_id=${encodeURIComponent(state.backendReportId)}`}
                target="_blank"
                className="inline-flex items-center gap-2 rounded-card border border-brand-border bg-brand-soft px-4 py-3 text-sm font-bold text-brand-strong transition hover:bg-surface"
                title={t.export.printTitle}
              >
                <Printer size={18} aria-hidden="true" />
                {t.export.print}
              </Link>
            ) : (
              <button
                className="inline-flex items-center gap-2 rounded-card border border-line bg-surface px-4 py-3 text-sm font-bold text-ink-muted disabled:opacity-60"
                disabled
              >
                {t.export.pdfLater}
              </button>
            )}
            <button className="inline-flex items-center gap-2 rounded-card border border-line bg-surface px-4 py-3 text-sm font-bold text-brand disabled:opacity-50" onClick={handleExportCha} disabled={!state.transcriptAttested || state.transcriptReviewStatus !== "reviewed"}><Download size={18} aria-hidden="true" />{t.export.cha}</button>
          </div>
        </div>
        {exportedCha ? <textarea className="mt-4 h-40 w-full rounded-panel border border-line bg-surface p-3 font-mono text-xs" readOnly value={exportedCha} aria-label={t.export.chaLabel} /> : null}
      </WorkspacePanel>
      <div className="min-w-0 space-y-5">
        {isStale ? (
          <div className="rounded-panel border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] p-4 text-sm text-[color:var(--color-warning-text)]" role="alert">
            <p className="font-semibold">{t.stale.title}</p>
            <p className="mt-1" id="stale-report-explanation">{t.stale.body}</p>
            <Link
              className="mt-3 inline-flex min-h-11 items-center rounded-card bg-[color:var(--color-warning-text)] px-4 font-semibold text-white"
              href={state.backendSessionId ? `/sessions/${state.backendSessionId}?view=findings` : "/cases?intent=start-session"}
            >
              {t.stale.regenerate}
            </Link>
          </div>
        ) : null}

        {hasSnapshotIntegrityError ? (
          <div className="rounded-panel border border-[color:var(--color-danger-border)] bg-[color:var(--color-danger-bg)] p-4 text-sm text-[color:var(--color-danger-text)]" role="alert">
            <p className="font-semibold">{t.integrity.errorTitle}</p>
            <p className="mt-1">{snapshotIntegrity.status === "invalid" ? snapshotIntegrity.reason : ""} {t.integrity.errorBody}</p>
          </div>
        ) : null}

        {isSnapshotIntegrityChecking ? (
          <div className="rounded-panel border border-brand-border bg-brand-soft p-4 text-sm text-brand" role="status" aria-live="polite">
            <p className="font-semibold">{t.integrity.checkingTitle}</p>
            <p className="mt-1">{t.integrity.checkingBody}</p>
          </div>
        ) : null}

        {identityLoaded && canRenderReportMetadata ? (
          <details className="rounded-shell border border-line bg-surface">
            <summary className="flex min-h-14 cursor-pointer items-start justify-between gap-3 px-5 py-4">
              <span className="min-w-0">
                <span className="block font-semibold text-ink">{t.metadata.summary}</span>
                <span className="mt-0.5 block text-sm text-ink-muted">{t.metadata.summaryHint}</span>
                <span className="mt-2 block">
              {signedSnapshotVerified ? (
                <span className="inline-block rounded-full bg-[color:var(--color-success-bg)] px-3 py-1 text-xs font-bold text-[color:var(--color-success-text)]">{t.provenance.signed}</span>
              ) : isSnapshotIntegrityChecking ? (
                <span className="rounded-full border border-brand-border bg-brand-soft px-3 py-1 text-xs font-bold text-brand">{t.provenance.verifying}</span>
              ) : hasSnapshotIntegrityError ? (
                <span className="rounded-full bg-[color:var(--color-danger-bg)] px-3 py-1 text-xs font-bold text-[color:var(--color-danger-text)]">{t.provenance.integrityError}</span>
              ) : isStale ? (
                <span className="rounded-full bg-[color:var(--color-warning-bg)] px-3 py-1 text-xs font-bold text-[color:var(--color-warning-text)]">{t.provenance.stale}</span>
              ) : isFailedSafety ? (
                <span className="rounded-full bg-[color:var(--color-danger-bg)] px-3 py-1 text-xs font-bold text-[color:var(--color-danger-text)]">{t.provenance.safetyFailed}</span>
              ) : isNotStarted ? (
                <span className="rounded-full bg-surface-muted px-3 py-1 text-xs font-bold text-ink">{t.provenance.neverGenerated}</span>
              ) : (
                <span className="rounded-full bg-brand-soft px-3 py-1 text-xs font-bold text-brand-strong">{t.provenance.editable}</span>
              )}
                </span>
              </span>
              <span aria-hidden="true" className="mt-0.5 text-ink-subtle">›</span>
            </summary>
            <div className="space-y-5 border-t border-line p-5">
          <section aria-label={t.provenance.title}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-bold text-ink">{t.provenance.title}</h2>
                <p className="mt-1 text-sm leading-6 text-ink-muted">{t.provenance.note}</p>
              </div>
            </div>
            <dl className="mt-4 grid gap-3 sm:grid-cols-2">
              <ReportProvenanceItem
                label={t.provenance.reviewedTranscript}
                value={versionLabel(reportGeneratedVersion(backendReport, state, "transcript_version") ?? (isFinalized ? undefined : state.backendTranscriptVersion))}
              />
              <ReportProvenanceItem label={t.provenance.reportVersion} value={versionLabel(isFinalized ? signedSnapshotNumber(backendReport, "report_version") : backendReport?.version ?? state.backendReportVersion)} />
              <ReportProvenanceItem label={t.provenance.featureResultId} value={(isFinalized ? signedSnapshotString(backendReport, "feature_result_id") : backendReport?.feature_result_id ?? state.featureSetId) ?? t.provenance.unavailable} />
              <ReportProvenanceItem
                label={t.provenance.schemaVersion}
                value={String(reportGeneratedVersion(backendReport, state, "schema_version") ?? (isFinalized ? undefined : backendReport?.feature_schema_version ?? state.featureSchemaVersion) ?? t.provenance.unavailable)}
              />
              <ReportProvenanceItem
                label={t.provenance.revision}
                value={isFinalized || backendReport?.revision_number == null ? t.provenance.unavailable : t.provenance.revisionNumber(backendReport.revision_number)}
              />
              {isFinalized ? (
                <>
                  <ReportProvenanceItem label={t.provenance.snapshotVersion} value={versionLabel(signedSnapshotNumber(backendReport, "report_version"))} />
                  <ReportProvenanceItem label={t.provenance.snapshotHash} value={signedSnapshotString(backendReport, "report_hash") ?? t.provenance.unavailable} />
                  <ReportProvenanceItem label={t.provenance.signedBy} value={signedSnapshotString(backendReport, "signed_by") ?? t.provenance.unavailable} />
                  <ReportProvenanceItem label={t.provenance.signedAt} value={signedSnapshotString(backendReport, "signed_at") ?? t.provenance.unavailable} />
                </>
              ) : null}
            </dl>
          </section>
          <section aria-label={t.source.title} className="border-t border-line pt-5">
            <h2 className="text-lg font-bold text-ink">{t.source.title}</h2>
            <p className="mt-1 text-sm leading-6 text-ink-muted">{t.source.note}</p>
            <dl className="mt-4 grid gap-3 sm:grid-cols-2">
              <ReportProvenanceItem label={t.source.requestedProvider} value={reportMetadataString(backendReport, "requested_provider") ?? t.provenance.unavailable} />
              <ReportProvenanceItem label={t.source.actualProvider} value={reportMetadataString(backendReport, "actual_provider") ?? t.provenance.unavailable} />
              <ReportProvenanceItem label={t.source.providerVersion} value={reportMetadataString(backendReport, "provider_version") ?? t.provenance.unavailable} />
              <ReportProvenanceItem label={t.source.fallbackReason} value={(isFinalized ? signedSnapshotProviderString(backendReport, "fallback_reason") : backendReport?.fallback_reason) ?? t.provenance.unavailable} />
              <ReportProvenanceItem label={t.source.validatorVersion} value={(isFinalized ? finalizedSafetyMetadataString(backendReport, "validator_version") : backendReport?.validator_version) ?? t.provenance.unavailable} />
              <ReportProvenanceItem label={t.source.ruleSetVersion} value={(isFinalized ? finalizedSafetyMetadataString(backendReport, "rule_set_version") : backendReport?.rule_set_version) ?? t.provenance.unavailable} />
              <ReportProvenanceItem label={t.source.finalizedSafety} value={finalizedSafetyLabel(backendReport)} />
              <ReportProvenanceItem label={t.source.inputHash} value={(isFinalized ? signedSnapshotString(backendReport, "input_hash") : backendReport?.input_hash) ?? t.provenance.unavailable} />
            </dl>
          </section>
            </div>
          </details>
        ) : null}

        {identityLoaded ? (
          <section aria-label={t.states.regionLabel} className="rounded-shell border border-line bg-surface p-5">
            <h2 className="text-lg font-bold text-ink">{t.states.title}</h2>
            <dl className="mt-4 grid gap-3 sm:grid-cols-3">
              <ReportProvenanceItem label={t.states.save} value={isSnapshotIntegrityChecking ? t.states.verifyingSnapshot : hasSnapshotIntegrityError ? t.states.integrityError : isNotStarted ? t.states.neverGenerated : reportSaveStateLabel(state.reportSaveStatus, isFinalized, isStale)} />
              <ReportProvenanceItem label={t.states.signOff} value={isSnapshotIntegrityChecking ? t.states.signedVerifying : hasSnapshotIntegrityError ? t.states.signedInvalid : isFinalized ? t.states.signed : isStale ? t.states.blockedRegenerate : isNotStarted ? t.states.blockedGenerate : t.states.confirmationRequired} />
              <ReportProvenanceItem label={t.states.reportExport} value={isSnapshotIntegrityChecking ? t.states.blockedVerifying : hasSnapshotIntegrityError ? t.states.blockedIntegrity : isFinalized ? t.states.eligible : isStale ? t.states.blockedRegenerate : isNotStarted ? t.states.blockedGenerate : t.states.afterSignOff} />
              <ReportProvenanceItem label={t.states.cuesAcknowledgement} value={state.cuesAcknowledgedAt ? `${state.cuesAcknowledgedBy ?? t.states.therapist} — ${formatDate(state.cuesAcknowledgedAt, locale)}` : t.states.notRecorded} />
            </dl>
          </section>
        ) : null}

        {identityLoaded && !isFinalized ? <WorkspacePanel className="divide-y divide-line/70 p-5">
          {reportSections.map((section) => {
            const Icon = section.icon;
            return (
              <div key={section.title} className="flex gap-4 py-4 first:pt-0 last:pb-0">
                <Icon size={22} aria-hidden="true" className="mt-1 shrink-0 text-brand" />
                <div>
                  <h3 className="text-lg font-bold text-ink">{section.title}</h3>
                  <ul className="mt-2 space-y-1 text-sm text-ink">
                    {section.items.map((item) => <li key={item}>• {item}</li>)}
                  </ul>
                </div>
              </div>
            );
          })}
        </WorkspacePanel> : null}

        {!isFinalized ? <>
        <WorkspacePanel className="p-5 space-y-4">
          <h2 className="text-lg font-bold text-ink">{t.inputs.title}</h2>
          <div>
            <label className="block text-sm font-semibold text-ink" htmlFor="therapist-notes">{t.inputs.notes}</label>
            <textarea id="therapist-notes" aria-label={t.inputs.notes} className="mt-2 min-h-24 w-full rounded-card border border-line bg-surface p-3 outline-none focus:ring-2 focus:ring-brand text-sm" value={therapistNotes} readOnly={isEditorLocked} onChange={(event) => {
              if (isEditorLocked) return;
              setTherapistNotes(event.target.value);
              persist({ ...state, reportSaveStatus: "unsaved", statusMessage: "Unsaved report edits.", error: undefined });
            }} />
          </div>
          <div>
            <label className="mt-2 block text-sm font-semibold text-ink" htmlFor="therapy-goals">{t.inputs.goals}</label>
            <textarea id="therapy-goals" aria-label={t.inputs.goals} className="mt-2 min-h-24 w-full rounded-card border border-line bg-surface p-3 outline-none focus:ring-2 focus:ring-brand text-sm" value={goalsText} readOnly={isEditorLocked} onChange={(event) => {
              if (isEditorLocked) return;
              setGoalsText(event.target.value);
              persist({ ...state, reportSaveStatus: "unsaved", statusMessage: "Unsaved report edits.", error: undefined });
            }} />
          </div>
        </WorkspacePanel>

        <details className="rounded-shell border border-line bg-surface">
          <summary className="flex min-h-14 cursor-pointer items-center justify-between gap-3 px-5 py-3 font-semibold text-ink">
            <span>{t.assistant.summary}</span>
            <span aria-hidden="true" className="text-ink-subtle">›</span>
          </summary>
          <div className="space-y-4 border-t border-line p-5">
          <h2 className="text-lg font-bold text-ink">{t.assistant.title}</h2>
          <div>
            <label className="block text-sm font-semibold text-ink" htmlFor="provider-selector">{t.assistant.provider}</label>
            <select
              id="provider-selector"
              className="mt-2 w-full rounded-card border border-line bg-surface p-3 text-sm font-medium focus:ring-2 focus:ring-brand outline-none"
              value={providerId}
              disabled={isEditorLocked}
              onChange={(e) => setProviderId(e.target.value)}
            >
              <option value="template">{t.assistant.template}</option>
              <option value="local_llm">{t.assistant.localLlm}</option>
            </select>
          </div>
          {providerId === "local_llm" && (
            <label className="flex min-h-11 cursor-pointer select-none items-center gap-3 text-sm">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-line text-brand focus:ring-brand focus:ring-offset-0"
                checked={allowFallback}
                disabled={isEditorLocked}
                onChange={(e) => setAllowFallback(e.target.checked)}
              />
              <span className="text-ink font-medium">
                {t.assistant.allowFallback}
              </span>
            </label>
          )}
          </div>
        </details>
        </> : null}

        {!isFinalized && !isFailedSafety && !isStale && (
          <WorkspacePanel className="p-5 space-y-4 animate-fade-in border border-line">
            <h2 className="text-lg font-bold text-ink">{t.signOff.title}</h2>
            <div className="rounded-panel border border-line bg-surface p-4">
              <p className="text-sm font-semibold text-ink">{t.signOff.primaryTherapist}</p>
              <p className="mt-2 text-sm text-ink">{primaryTherapistLabel}</p>
              <p className="mt-2 text-xs leading-5 text-ink-muted">
                {t.signOff.identityNote}
              </p>
            </div>
            {!primaryTherapistAssigned ? (
              <p className="rounded-card border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] p-3 text-sm font-semibold text-[color:var(--color-warning-text)]">
                {t.signOff.assignFirst}
              </p>
            ) : null}
            <label className="flex min-h-11 cursor-pointer select-none items-start gap-3 text-sm">
              <input
                type="checkbox"
                className="mt-1 h-4 w-4 shrink-0 rounded border-line text-brand focus:ring-brand focus:ring-offset-0"
                checked={confirmationChecked}
                onChange={(e) => setConfirmationChecked(e.target.checked)}
              />
              <span className="text-ink font-medium">
                {t.signOff.confirm}
              </span>
            </label>
          </WorkspacePanel>
        )}

        <WorkspacePanel className="p-5">
          <h2 className="text-lg font-bold text-ink">{t.share.title}</h2>
          <p className="mt-2 text-sm leading-6 text-ink-muted">
            {t.share.note}
          </p>
          <p className="mt-2 font-bold text-brand">{state.shareStatus}</p>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <button className="inline-flex min-h-11 items-center justify-center gap-2 rounded-card border border-line bg-surface px-3 font-semibold" disabled={!identityLoaded || isStale || signedActionsBlocked} onClick={handleCopyLocalDemoShareLink}>
              <Clipboard size={17} aria-hidden="true" /> {t.share.copyLink}
            </button>
            <button className="inline-flex min-h-11 items-center justify-center gap-2 rounded-card border border-line bg-surface px-3 font-semibold" disabled={!identityLoaded || isStale || signedActionsBlocked} onClick={handleMarkSent}>
              <Send size={17} aria-hidden="true" /> {t.share.markSent}
            </button>
          </div>
        </WorkspacePanel>

        <Button
          icon={ShieldCheck}
          size="lg"
          variant={nextAction === "finalize" ? "primary" : "secondary"}
          className="w-full"
          onClick={handleFinalize}
          disabled={isFinalizeDisabled}
          data-testid="finalize-report-button"
        >
          {isFinalized ? t.signOff.finalized : backendUnavailable ? t.signOff.finalizeOnlineOnly : t.signOff.finalize}
        </Button>
        {isFinalized ? (
          <button
            type="button"
            className="inline-flex min-h-11 w-full items-center justify-center rounded-card border border-brand bg-surface px-4 text-sm font-bold text-brand disabled:opacity-50"
            onClick={() => void handleCreateRevision()}
            disabled={busy || backendUnavailable || signedActionsBlocked || !(backendReport?.report_id ?? state.reportId)}
          >
            {busy ? t.signOff.creatingRevision : t.signOff.createRevision}
          </button>
        ) : null}
        {state.finalizeStatus ? <p className="demo-note rounded-panel p-3 text-sm">{state.finalizeStatus}</p> : null}
        <WorkflowStatus state={state} backendUnavailable={backendUnavailable} />
        <SafetyNote>{safety.NON_DIAGNOSTIC_CLAIM} {t.finalTextNote}</SafetyNote>
      </div>

      </div>
    </>
  );
}

export type { SessionReportViewProps } from "@/features/sessions/report/use-session-report";
