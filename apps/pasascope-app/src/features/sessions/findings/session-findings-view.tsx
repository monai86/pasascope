"use client";

import { useEffect, useMemo, useState } from "react";
import { FileSearch, FileText, ShieldCheck, Wand2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { PrimaryActionButton, WorkspacePanel } from "@/components/workbench-ui";
import { RightRail } from "@/components/right-rail";
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
            <PrimaryActionButton href={workflowSessionHref("transcript", state)} icon={FileText}>{t.empty.reviewTranscript}</PrimaryActionButton>
          </div>
          <PrimaryActionButton icon={ShieldCheck} className="mt-3" disabled>{t.actions.generateReport}</PrimaryActionButton>
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
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
      <div className="space-y-6">
        {findingsStale ? (
          <p role="alert" className="text-sm leading-6 text-[color:var(--color-warning-text)]">
            {t.staleAlert}
          </p>
        ) : null}

        <section className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-ink">{t.signals.title}</h2>
              <p className="mt-2 text-sm leading-6 text-ink-muted">
                {findingsStale
                  ? t.signals.staleNote
                  : t.signals.note}
              </p>
            </div>
            {currentFindingsState.featuresExtracted && !currentFindingsState.mlDecisionSupport ? (
              <div className="space-y-2">
                <PrimaryActionButton
                  icon={Wand2}
                  onClick={onGenerateMlDecisionSupport}
                  disabled={busy || backendUnavailable || currentFindingsState.mlReadiness?.ready === false}
                  data-testid="generate-evidence-review-button"
                  aria-describedby={evidenceReviewReason ? "generate-evidence-review-reason" : undefined}
                >
                  {busy ? t.signals.generating : t.signals.generateEvidenceReview}
                </PrimaryActionButton>
                {evidenceReviewReason ? (
                  <p id="generate-evidence-review-reason" role="status" className="rounded-card border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] px-3 py-2 text-sm font-semibold text-[color:var(--color-warning-text)]">
                    {evidenceReviewReason}
                  </p>
                ) : null}
              </div>
            ) : null}
          </div>
          {currentFindingsState.featuresExtracted ? (
            <FeatureDecisionGrid signals={signalCards} />
          ) : null}
        </section>

        <section aria-labelledby="findings-workflow-summary-title" className="overflow-hidden rounded-panel border border-line bg-line">
          <div className="bg-surface px-4 py-3">
            <h2 id="findings-workflow-summary-title" className="text-sm font-semibold text-ink">{t.summary.title}</h2>
          </div>
          <dl className="grid gap-px sm:grid-cols-2 xl:grid-cols-4">
            <div className="bg-surface px-4 py-3">
              <dt className="text-xs font-medium uppercase tracking-[0.08em] text-ink-subtle">{t.summary.transcriptQuality}</dt>
              <dd className="mt-1 font-semibold text-ink">{label(transcriptQualityLabel(state))}</dd>
              <p className="mt-1 text-xs leading-5 text-ink-muted">{state.qaSummary ?? safety.THERAPIST_REVIEW_REMAINS_REQUIRED}</p>
            </div>
            <div className="bg-surface px-4 py-3">
              <dt className="text-xs font-medium uppercase tracking-[0.08em] text-ink-subtle">{t.summary.featuresExtracted}</dt>
              <dd className="mt-1 font-semibold text-ink">{currentFindingsState.featuresExtracted ? t.summary.signalCount(signalCards.length) : t.summary.pending}</dd>
              <p className="mt-1 text-xs leading-5 text-ink-muted">{currentFindingsState.featuresExtracted ? t.summary.featuresAvailable : t.summary.featuresMissing}</p>
            </div>
            <div className="bg-surface px-4 py-3">
              <dt className="text-xs font-medium uppercase tracking-[0.08em] text-ink-subtle">{t.summary.reviewFlags}</dt>
              <dd className="mt-1 font-semibold text-ink">{totalReviewFlags(currentFindingsState)}</dd>
              <p className="mt-1 text-xs leading-5 text-ink-muted">{totalReviewFlags(currentFindingsState) > 0 ? t.summary.flagsOpen : t.summary.flagsNone}</p>
            </div>
            <div className="bg-surface px-4 py-3">
              <dt className="text-xs font-medium uppercase tracking-[0.08em] text-ink-subtle">{t.summary.reportReadiness}</dt>
              <dd className="mt-1 font-semibold text-ink">{reportReady ? t.summary.ready : t.summary.blocked}</dd>
              <p className="mt-1 text-xs leading-5 text-ink-muted">{reportReady ? t.summary.gatesPassed : t.summary.gatesMissing}</p>
            </div>
          </dl>
        </section>

        <ProgressSummaryCard state={state} aiReview={state.aiReview} busy={busy} onGenerateAiReview={onGenerateAiReview} />

        <details className="responsive-details rounded-shell border border-line bg-surface">
          <summary className="flex min-h-14 cursor-pointer items-center justify-between gap-3 px-5 py-3">
            <span>
              <span className="block font-semibold text-ink">{t.provenance.title}</span>
              <span className="mt-0.5 block text-sm text-ink-muted">{t.provenance.subtitle}</span>
            </span>
            <span className={`rounded-full px-3 py-1 text-xs font-semibold ${findingsCurrent ? "bg-[color:var(--color-success-bg)] text-[color:var(--color-success-text)]" : "bg-[color:var(--color-warning-bg)] text-[color:var(--color-warning-text)]"}`}>
              {label(analysisDispositionLabel(state.analysisStatus))}
            </span>
          </summary>
          <section aria-label={t.provenance.regionLabel} className="border-t border-line p-5">
            <p className="text-sm leading-6 text-ink-muted">
              {t.provenance.note}
            </p>
            <dl className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
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
        </details>

        <section className="grid gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
          <EvidenceReviewSection
            mlDecisionSupport={currentFindingsState.mlDecisionSupport}
            recommendedReviewPoints={recommendedReviewPoints}
            busy={busy}
            onProfileEvidenceReview={onProfileEvidenceReview}
            onCueReview={onCueReview}
            transcriptLines={currentFindingsState.transcriptLines}
            transcriptHref={resolveSessionHref("transcript", sessionContext.sessionId)}
          />

          <div className="space-y-6">
            <section className="rounded-shell border border-line bg-surface p-6">
              <h2 className="text-xl font-semibold text-ink">{t.actions.title}</h2>
              <div className="mt-4 space-y-3">
                <button
                  type="button"
                  className="flex min-h-11 w-full items-center justify-center rounded-card border border-line bg-surface px-4 py-3 text-sm font-semibold text-ink disabled:cursor-not-allowed disabled:opacity-50"
                  onClick={() => onApproveReviewedCues()}
                  disabled={busy || findingsStale || (!currentFindingsState.mlDecisionSupport && signalCards.length === 0)}
                  aria-describedby={approveCuesReason ? "approve-reviewed-cues-reason" : undefined}
                >
                  {t.actions.approveCues}
                </button>
                {approveCuesReason ? (
                  <p id="approve-reviewed-cues-reason" role="status" className="rounded-card border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] px-3 py-2 text-sm font-semibold text-[color:var(--color-warning-text)]">
                    {approveCuesReason}
                  </p>
                ) : null}
                {/* Generating the report is the next step here; going back to the transcript is secondary. */}
                <Button href={workflowSessionHref("transcript", state)} icon={FileText} variant="secondary" className="w-full">
                  {t.actions.reviseTranscript}
                </Button>
                <button
                  type="button"
                  className="flex min-h-11 w-full items-center justify-center rounded-full bg-brand px-4 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
                  onClick={onGenerateReport}
                  disabled={busy || !reportReady}
                  data-testid="generate-report-button"
                >
                  {busy ? t.actions.generating : t.actions.generateReport}
                </button>
              </div>
              {!reportReady ? (
                <p className="mt-4 text-sm text-[color:var(--color-warning-text)]">
                  {t.actions.notReady}
                </p>
              ) : null}
              {state.cuesAcknowledgedAt ? (
                <p className="mt-3 text-sm text-[color:var(--color-success-text)]">
                  {t.actions.acknowledged(state.cuesAcknowledgedBy, formatDate(state.cuesAcknowledgedAt, locale))}
                </p>
              ) : null}
            </section>

            <section className="rounded-shell border border-line bg-surface p-6">
              <h2 className="text-xl font-semibold text-ink">{t.draft.title}</h2>
              <p className="mt-2 text-sm leading-6 text-ink-muted">
                {t.draft.note}
              </p>
              <textarea
                aria-label={t.draft.title}
                className="mt-4 min-h-48 w-full rounded-panel border border-line bg-surface p-4 text-sm leading-6 text-ink"
                value={interpretationDraft}
                readOnly={findingsStale}
                onChange={(event) => setInterpretationDraft(event.target.value)}
              />
            </section>
          </div>
        </section>

        <WorkflowStatus state={state} backendUnavailable={backendUnavailable} />
      </div>

      <RightRail
        title={t.rail.title}
        description={t.rail.description}
      >
        <div className="rounded-panel border border-line bg-surface p-4">
          <h3 className="text-sm font-semibold text-ink">{t.rail.readiness}</h3>
          <ul className="mt-3 space-y-2 text-sm text-ink-muted">
            <li>{state.transcriptAttested ? t.rail.attested : t.rail.attestationRequired}</li>
            <li>{currentFindingsState.featuresExtracted ? t.rail.extractionComplete : t.rail.extractionPending}</li>
            <li>{currentFindingsState.mlReadiness?.ready === false ? t.rail.evidenceBlocked : t.rail.evidenceCanProceed}</li>
          </ul>
        </div>
        <div className="rounded-panel border border-line bg-surface p-4">
          <h3 className="text-sm font-semibold text-ink">{t.rail.referenceStatus}</h3>
          <p className="mt-2 text-sm leading-6 text-ink-muted">
            {missingReferenceData ? t.rail.referenceUnavailable : t.rail.referenceNote}
          </p>
        </div>
        <details className="responsive-details rounded-panel border border-line bg-surface">
          <summary className="flex min-h-11 cursor-pointer items-center justify-between gap-3 px-4 text-sm font-semibold text-ink">
            <span>{t.rail.limitations}</span>
            <span aria-hidden="true">›</span>
          </summary>
          <ul className="border-t border-line px-4 py-3 pl-9 text-sm text-ink-muted">
            {(currentFindingsState.mlDecisionSupport?.limitations.length
              ? currentFindingsState.mlDecisionSupport.limitations
              : t.rail.defaultLimitations).map((limitation) => <li className="list-disc" key={limitation}>{limitation}</li>)}
          </ul>
        </details>
      </RightRail>
      </div>
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
