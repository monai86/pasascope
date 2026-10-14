"use client";

import { useEffect, useMemo, useState } from "react";
import { FileSearch, FileText, ShieldCheck, Wand2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { PrimaryActionButton, WorkspacePanel } from "@/components/workbench-ui";
import { SessionContextHeader, type SessionContext } from "@/features/sessions/components/session-context-header";
import { SessionGuide, type SessionGuideAction } from "@/features/sessions/components/session-guide";
import { resolveSessionHref } from "@/features/sessions/state/session-view";
import { EvidenceReviewSection } from "@/features/sessions/findings/evidence-review-section";
import { FeatureDecisionGrid } from "@/features/sessions/findings/feature-decision-grid";
import { findingsMessages } from "@/features/sessions/findings/findings.messages";
import { ProgressSummaryCard } from "@/features/sessions/findings/progress-summary-card";
import {
  ProvenanceItem,
  WorkflowStatus,
  analysisDispositionLabel,
  buildLinguisticSignalCards,
  buildRecommendedReviewPoints,
  createInterpretationDraft,
  evidenceDisposition,
  hasMissingReferenceData,
  isResultsReportReady,
  isTranscriptUnlocked,
  totalReviewFlags,
  transcriptQualityLabel,
  versionLabel,
  workflowSessionHref,
} from "@/features/sessions/findings/session-findings-support";
import { approveReviewedCuesBlockedReason, generateEvidenceReviewBlockedReason, regenerateFindingsBlockedReason } from "@/lib/workflow-gates";
import { useSafetyCopy } from "@/lib/safety-copy";
import { formatDate } from "@/i18n/format";
import { useLocale, useMessages } from "@/i18n/locale-provider";
import type { WorkflowState } from "@/lib/workflow";
import { useGateReason } from "@/lib/gate-reason";
import { useFindingsLabel } from "@/features/sessions/findings/use-findings-label";

export function SessionFindingsView({
  sessionContext,
  state,
  busy,
  onRegenerateFindings,
  onGenerateReport,
  onGenerateMlDecisionSupport,
  onGenerateAiReview,
  onProfileEvidenceReview,
  onCueReview,
  onApproveReviewedCues,
  backendUnavailable
}: {
  sessionContext: SessionContext;
  state: WorkflowState;
  busy: boolean;
  onRegenerateFindings: () => void;
  onGenerateReport: () => void;
  onGenerateMlDecisionSupport: () => void;
  onGenerateAiReview: () => void;
  onProfileEvidenceReview: (
    profileCode: "TD" | "DD" | "ASD" | "LT" | "STI" | "HL",
    status: "reviewed" | "disagreement",
    therapistNote?: string
  ) => void;
  onCueReview?: (cueCode: string, status: "acknowledged" | "dismissed") => void;
  onApproveReviewedCues: () => void | Promise<void>;
  backendUnavailable?: boolean;
}) {
  const findingsStale = state.analysisStatus === "stale";
  const findingsCurrent = state.analysisStatus === "completed";
  const currentFindingsState = useMemo(() => !findingsCurrent ? {
    ...state,
    featuresExtracted: false,
    featurePercent: 0,
    featureSummary: [],
    featureSignals: [],
    mlDecisionSupport: undefined,
    insights: [],
  } : state, [findingsCurrent, state]);
  const t = useMessages(findingsMessages);
  const { locale } = useLocale();
  const safety = useSafetyCopy();
  const [interpretationDraft, setInterpretationDraft] = useState(() =>
    createInterpretationDraft(currentFindingsState.featureSignals, currentFindingsState.featureSummary, currentFindingsState.mlDecisionSupport)
  );
  const signalCards = useMemo(() => buildLinguisticSignalCards(currentFindingsState), [currentFindingsState]);
  const recommendedReviewPoints = useMemo(() => buildRecommendedReviewPoints(currentFindingsState), [currentFindingsState]);
  const interpretationDraftSeed = useMemo(
    () => createInterpretationDraft(currentFindingsState.featureSignals, currentFindingsState.featureSummary, currentFindingsState.mlDecisionSupport),
    [currentFindingsState.featureSignals, currentFindingsState.featureSummary, currentFindingsState.mlDecisionSupport]
  );
  const reportReady = isResultsReportReady(state);
  const missingReferenceData = hasMissingReferenceData(currentFindingsState);
  const gate = useGateReason();
  const label = useFindingsLabel();
  const regenerateFindingsReason = gate(regenerateFindingsBlockedReason(state));
  const evidenceReviewReason = gate(generateEvidenceReviewBlockedReason({
    backendUnavailable,
    readiness: currentFindingsState.mlReadiness,
  }));
  const approveCuesReason = gate(approveReviewedCuesBlockedReason({
    busy,
    findingsStale,
    hasReviewableCues: Boolean(currentFindingsState.mlDecisionSupport) || signalCards.length > 0,
  }));

  useEffect(() => {
    setInterpretationDraft(interpretationDraftSeed);
  }, [interpretationDraftSeed, state.backendSessionId, state.reportId]);

  if (!state.transcriptReady && !state.featuresExtracted) {
    return (
      <div className="mx-auto max-w-7xl space-y-6">
        <SessionContextHeader
          title={t.title}
          description={t.emptyDescription}
          context={sessionContext}
        />
        <WorkspacePanel className="p-8 text-center">
          <FileSearch className="mx-auto text-brand" size={38} aria-hidden="true" />
          <h2 className="mt-3 text-xl font-bold text-ink">{t.empty.title}</h2>
          <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-ink-muted">
            {t.empty.body}
          </p>
          <div className="mt-5 flex flex-wrap justify-center gap-3">
            <PrimaryActionButton href={workflowSessionHref("intake", state)} icon={FileText}>{t.empty.addTranscript}</PrimaryActionButton>
            <Button href={workflowSessionHref("transcript", state)} icon={FileText} variant="secondary">{t.empty.reviewTranscript}</Button>
          </div>
          <Button icon={ShieldCheck} variant="secondary" className="mt-3" disabled>{t.actions.generateReport}</Button>
        </WorkspacePanel>
      </div>
    );
  }
  return (
    <div className="space-y-6">
      <SessionContextHeader
        title={t.title}
        description={t.description}
        context={sessionContext}
        density="compact"
      />
      <SessionGuide
        testId="findings-guide"
        reasonId={findingsStale ? "regenerate-findings-reason" : undefined}
        prompt={
          findingsStale
            ? t.guide.stale
            : reportReady
              ? t.guide.ready
              : t.guide.review
        }
        primaryAction={findingsGuidePrimary({
          findingsStale,
          busy,
          regenerateFindingsReason,
          onRegenerateFindings,
          state,
          label: t.guide.regenerate,
        })}
        quickReplies={
          findingsStale
            ? [
                { label: t.guide.reviseTranscript, href: resolveSessionHref("transcript", sessionContext.sessionId) },
                { label: t.guide.goToReport, href: resolveSessionHref("report", sessionContext.sessionId) },
              ]
            : [
                { label: t.guide.reviseTranscript, href: resolveSessionHref("transcript", sessionContext.sessionId) },
                { label: t.guide.regenerate, onClick: onRegenerateFindings },
                { label: t.guide.goToReport, href: resolveSessionHref("report", sessionContext.sessionId) },
              ]
        }
      />
      <div className="space-y-6">
        {findingsStale ? (
          <p role="alert" className="text-sm leading-6 text-[color:var(--color-warning-text)]">
            {t.staleAlert}
          </p>
        ) : null}

        {/* The values first: everything that was extracted, in one place. */}
        {currentFindingsState.featuresExtracted ? (
          <FeatureDecisionGrid signals={signalCards} />
        ) : (
          <p className="rounded-panel border border-line bg-surface px-5 py-6 text-sm leading-6 text-ink-muted">
            {findingsStale ? t.signals.staleNote : t.signals.note}
          </p>
        )}

        {/* What to do with them, right under them. */}
        <section aria-labelledby="findings-actions-title" className="rounded-panel border border-line bg-surface px-5 py-5 sm:px-7">
          <h2 id="findings-actions-title" className="sr-only">{t.actions.title}</h2>
          <div className="flex flex-wrap items-center gap-3">
            <Button
              onClick={onGenerateReport}
              disabled={busy || !reportReady}
              data-testid="generate-report-button"
            >
              {busy ? t.actions.generating : t.actions.generateReport}
            </Button>
            <Button
              variant="secondary"
              onClick={() => onApproveReviewedCues()}
              disabled={busy || findingsStale || (!currentFindingsState.mlDecisionSupport && signalCards.length === 0)}
              aria-describedby={approveCuesReason ? "approve-reviewed-cues-reason" : undefined}
            >
              {t.actions.approveCues}
            </Button>
            {currentFindingsState.featuresExtracted && !currentFindingsState.mlDecisionSupport ? (
              <Button
                variant="secondary"
                icon={Wand2}
                onClick={onGenerateMlDecisionSupport}
                disabled={busy || backendUnavailable || currentFindingsState.mlReadiness?.ready === false}
                data-testid="generate-evidence-review-button"
                aria-describedby={evidenceReviewReason ? "generate-evidence-review-reason" : undefined}
              >
                {busy ? t.signals.generating : t.signals.generateEvidenceReview}
              </Button>
            ) : null}
          </div>
          <div className="mt-3 space-y-1 text-sm leading-6">
            {!reportReady ? <p className="text-[color:var(--color-warning-text)]">{t.actions.notReady}</p> : null}
            {approveCuesReason ? (
              <p id="approve-reviewed-cues-reason" role="status" className="text-[color:var(--color-warning-text)]">{approveCuesReason}</p>
            ) : null}
            {evidenceReviewReason ? (
              <p id="generate-evidence-review-reason" role="status" className="text-[color:var(--color-warning-text)]">{evidenceReviewReason}</p>
            ) : null}
            {state.cuesAcknowledgedAt ? (
              <p className="text-[color:var(--color-success-text)]">
                {t.actions.acknowledged(state.cuesAcknowledgedBy, formatDate(state.cuesAcknowledgedAt, locale))}
              </p>
            ) : null}
          </div>
        </section>

        <section aria-labelledby="findings-draft-title" className="rounded-panel border border-line bg-surface px-5 py-6 sm:px-7">
          <h2 id="findings-draft-title" className="text-lg font-semibold text-ink">{t.draft.title}</h2>
          <p className="mt-1 max-w-[62ch] text-sm leading-6 text-ink-muted">{t.draft.note}</p>
          <textarea
            aria-label={t.draft.title}
            className="mt-4 min-h-40 w-full rounded-control border border-line bg-surface p-4 text-[15px] leading-7 text-ink"
            value={interpretationDraft}
            readOnly={findingsStale}
            onChange={(event) => setInterpretationDraft(event.target.value)}
          />
        </section>

        <EvidenceReviewSection
          mlDecisionSupport={currentFindingsState.mlDecisionSupport}
          recommendedReviewPoints={recommendedReviewPoints}
          busy={busy}
          onProfileEvidenceReview={onProfileEvidenceReview}
          onCueReview={onCueReview}
          transcriptLines={currentFindingsState.transcriptLines}
          transcriptHref={resolveSessionHref("transcript", sessionContext.sessionId)}
        />

        <ProgressSummaryCard state={state} aiReview={state.aiReview} busy={busy} onGenerateAiReview={onGenerateAiReview} />

        {/* Everything that explains the values rather than being them, folded together. */}
        <details className="responsive-details rounded-panel border border-line bg-surface">
          <summary className="flex min-h-14 cursor-pointer items-center justify-between gap-3 px-5 py-3 sm:px-7">
            <h2 className="text-base font-semibold text-ink">{t.rail.title}</h2>
            <span className={`rounded-full px-3 py-1 text-xs font-semibold ${findingsCurrent ? "bg-[color:var(--color-success-bg)] text-[color:var(--color-success-text)]" : "bg-[color:var(--color-warning-bg)] text-[color:var(--color-warning-text)]"}`}>
              {label(analysisDispositionLabel(state.analysisStatus))}
            </span>
          </summary>
          <div className="space-y-6 border-t border-line px-5 py-5 sm:px-7">
            <p className="text-sm leading-6 text-ink-muted">{t.rail.description}</p>
            <section aria-labelledby="findings-workflow-summary-title">
              <h3 id="findings-workflow-summary-title" className="text-sm font-semibold text-ink">{t.summary.title}</h3>
              <dl className="mt-2 divide-y divide-line border-y border-line text-sm">
                <SummaryRow label={t.summary.transcriptQuality} value={label(transcriptQualityLabel(state))} note={state.qaSummary ?? safety.THERAPIST_REVIEW_REMAINS_REQUIRED} />
                <SummaryRow label={t.summary.featuresExtracted} value={currentFindingsState.featuresExtracted ? t.summary.signalCount(signalCards.length) : t.summary.pending} note={currentFindingsState.featuresExtracted ? t.summary.featuresAvailable : t.summary.featuresMissing} />
                <SummaryRow label={t.summary.reviewFlags} value={String(totalReviewFlags(currentFindingsState))} note={totalReviewFlags(currentFindingsState) > 0 ? t.summary.flagsOpen : t.summary.flagsNone} />
                <SummaryRow label={t.summary.reportReadiness} value={reportReady ? t.summary.ready : t.summary.blocked} note={reportReady ? t.summary.gatesPassed : t.summary.gatesMissing} />
              </dl>
            </section>
            <section>
              <h3 className="text-sm font-semibold text-ink">{t.rail.referenceStatus}</h3>
              <p className="mt-1 text-sm leading-6 text-ink-muted">{missingReferenceData ? t.rail.referenceUnavailable : t.rail.referenceNote}</p>
            </section>
            <section>
              <h3 className="text-sm font-semibold text-ink">{t.rail.limitations}</h3>
              <ul className="mt-1 list-disc space-y-1 pl-5 text-sm leading-6 text-ink-muted">
                {(currentFindingsState.mlDecisionSupport?.limitations.length
                  ? currentFindingsState.mlDecisionSupport.limitations
                  : t.rail.defaultLimitations).map((limitation) => <li key={limitation}>{limitation}</li>)}
              </ul>
            </section>
            <section aria-label={t.provenance.regionLabel}>
              <h3 className="text-sm font-semibold text-ink">{t.provenance.title}</h3>
              <p className="mt-1 text-sm leading-6 text-ink-muted">{t.provenance.note}</p>
              <dl className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                <ProvenanceItem label={t.provenance.reviewedTranscript} value={label(versionLabel(state.backendTranscriptVersion))} />
                <ProvenanceItem label={t.provenance.findingsTranscript} value={label(versionLabel(state.featureTranscriptVersion))} />
                <ProvenanceItem label={t.provenance.featureResultId} value={state.featureSetId ?? t.provenance.unavailable} />
                <ProvenanceItem
                  label={t.provenance.schemaVersion}
                  value={state.featureSchemaVersion ?? currentFindingsState.mlDecisionSupport?.featureSchemaVersion ?? t.provenance.unavailable}
                />
                <ProvenanceItem
                  label={t.provenance.aiDisposition}
                  value={label(findingsCurrent ? evidenceDisposition(currentFindingsState.mlDecisionSupport) : analysisDispositionLabel(state.analysisStatus))}
                />
              </dl>
            </section>
          </div>
        </details>

        <WorkflowStatus state={state} backendUnavailable={backendUnavailable} />
      </div>
    </div>
  );
}

function SummaryRow({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="grid gap-1 py-2.5 sm:grid-cols-[minmax(0,12rem)_minmax(0,10rem)_minmax(0,1fr)] sm:gap-4">
      <dt className="font-medium text-ink-muted">{label}</dt>
      <dd className="font-semibold text-ink">{value}</dd>
      <dd className="text-ink-muted">{note}</dd>
    </div>
  );
}

function findingsGuidePrimary({
  findingsStale,
  busy,
  regenerateFindingsReason,
  onRegenerateFindings,
  state,
  label,
}: {
  label: string;
  findingsStale: boolean;
  busy: boolean;
  regenerateFindingsReason?: string;
  onRegenerateFindings: () => void;
  state: WorkflowState;
}): SessionGuideAction | undefined {
  // The guide owns the regeneration affordance when findings are stale (it
  // replaced the old banner). In every other state the page's own action panel
  // already carries the primary action, so the guide only prompts and navigates.
  if (findingsStale) {
    return {
      label,
      onClick: onRegenerateFindings,
      disabled: busy || !isTranscriptUnlocked(state),
      reason: regenerateFindingsReason,
    };
  }
  return undefined;
}
