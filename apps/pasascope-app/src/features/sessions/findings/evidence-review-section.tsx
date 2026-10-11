"use client";

import { useEffect, useRef, useState } from "react";

import type { WorkflowState } from "@/lib/workflow";
import {
  EvidenceAvailabilityView,
  featureLabel,
  patternEvidenceTitle,
  positionTitle,
  profileStatusTitle,
} from "@/features/sessions/findings/session-findings-support";
import { EVIDENCE_REVIEW_NOUN } from "@/lib/workflow-glossary";
import { NOT_DIAGNOSTIC_BADGE } from "@/lib/clinical-safety-copy";

export function EvidenceReviewSection({
  mlDecisionSupport,
  recommendedReviewPoints,
  busy,
  onProfileEvidenceReview,
  onCueReview,
  transcriptLines = [],
  transcriptHref,
}: {
  onCueReview?: (cueCode: string, status: "acknowledged" | "dismissed") => void;
  transcriptLines?: WorkflowState["transcriptLines"];
  transcriptHref?: string;
  mlDecisionSupport?: WorkflowState["mlDecisionSupport"];
  recommendedReviewPoints: string[];
  busy: boolean;
  onProfileEvidenceReview: (
    profileCode: "TD" | "DD" | "ASD" | "LT" | "STI" | "HL",
    status: "reviewed" | "disagreement",
    therapistNote?: string
  ) => void;
}) {
  const [showEvidenceDetails, setShowEvidenceDetails] = useState(false);
  const [disagreementProfile, setDisagreementProfile] = useState<string>();
  const [disagreementNote, setDisagreementNote] = useState("");

  // Open the panel when a review has been generated, so its result is not
  // hidden behind a collapsed summary. The therapist can still close it.
  const detailsRef = useRef<HTMLDetailsElement>(null);
  const reviewResultId = mlDecisionSupport?.resultId;
  useEffect(() => {
    if (reviewResultId && detailsRef.current) detailsRef.current.open = true;
  }, [reviewResultId]);

  const lineText = (lineId?: string) => transcriptLines.find((line) => line.lineId === lineId)?.text;

  let initialEvidenceCueCount = 0;

  return (
    <details ref={detailsRef} className="responsive-details self-start rounded-shell border border-line bg-surface">
      <summary className="flex min-h-14 cursor-pointer items-center justify-between gap-3 px-5 py-3">
        <span className="font-semibold text-ink">Review guidance and evidence</span>
        <span className="text-xs font-medium text-ink-muted">{recommendedReviewPoints.length} review point{recommendedReviewPoints.length === 1 ? "" : "s"}</span>
      </summary>
      <div className="border-t border-line p-5">
      <h2 className="text-lg font-semibold text-ink">Recommended review points</h2>
      <ul className="mt-4 space-y-3 text-sm leading-6 text-ink-muted">
        {recommendedReviewPoints.map((point) => (
          <li key={point} className="rounded-panel border border-line bg-surface px-4 py-3">
            {point}
          </li>
        ))}
      </ul>
      {mlDecisionSupport ? (
        <div className="mt-5 space-y-3" data-testid="evidence-review-panel">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-ink-muted">{EVIDENCE_REVIEW_NOUN}</h3>
            <span className="rounded-full bg-[color:var(--color-warning-bg)] px-3 py-1 text-xs font-bold text-[color:var(--color-warning-text)]">{NOT_DIAGNOSTIC_BADGE}</span>
          </div>
          <p className="text-sm text-ink-muted">
            {mlDecisionSupport.providerName} v{mlDecisionSupport.providerVersion} · schema {mlDecisionSupport.featureSchemaVersion}
          </p>
          {(mlDecisionSupport.cues ?? []).length > 0 ? (
            <ul className="space-y-3" data-testid="review-cue-list">
              {(mlDecisionSupport.cues ?? []).map((cue) => (
                <li key={cue.cueCode} className="rounded-panel border border-line bg-surface p-4">
                  <p className="font-semibold text-ink">{cue.title}</p>
                  <p className="mt-1 text-sm text-ink-muted">{cue.explanation}</p>
                  <p className="mt-2 text-sm text-ink-muted">
                    {Object.entries(cue.supportingFeatures).map(([name, value]) => `${name.replace(/_/g, " ")}: ${value ?? "not computed"}`).join(" · ")}
                  </p>
                  {(cue.evidence ?? []).length > 0 ? (
                    <ol className="mt-3 space-y-2" data-testid={`cue-evidence-${cue.cueCode}`}>
                      {(cue.evidence ?? []).map((item) => (
                        <li key={`${item.adultUtteranceId ?? ""}-${item.childUtteranceId}`} className="rounded-card border border-line bg-surface px-3 py-2 text-sm">
                          {item.adultUtteranceId ? (
                            <p className="text-ink-muted">
                              <span className="font-semibold">Adult:</span> {lineText(item.adultUtteranceId) ?? "(line no longer in transcript)"}
                            </p>
                          ) : null}
                          <p className="text-ink">
                            <span className="font-semibold">Child:</span> {lineText(item.childUtteranceId) ?? "(line no longer in transcript)"}
                          </p>
                          {item.category ? (
                            <p className="mt-1 text-xs text-ink-muted">
                              {item.category === "immediate_verbatim" ? "Repeats the adult turn" : "Repeats part of the adult turn"}
                            </p>
                          ) : null}
                        </li>
                      ))}
                    </ol>
                  ) : null}
                  <p className="mt-2 text-sm font-medium text-ink">Next: {cue.recommendedNextReviewStep}</p>
                  {cue.limitations.length > 0 ? (
                    <p className="mt-1 text-xs text-ink-muted">{cue.limitations.join(" ")}</p>
                  ) : null}
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    {cue.reviewStatus === "unreviewed" && onCueReview ? (
                      <>
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => onCueReview(cue.cueCode, "acknowledged")}
                          className="inline-flex min-h-11 items-center rounded-card bg-brand px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
                        >
                          Confirm after checking
                        </button>
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => onCueReview(cue.cueCode, "dismissed")}
                          className="inline-flex min-h-11 items-center rounded-card border border-line px-3 py-2 text-sm font-semibold text-ink disabled:opacity-60"
                        >
                          Dismiss — not an echo or pronoun issue
                        </button>
                      </>
                    ) : (
                      <span className="rounded-full bg-surface-muted px-3 py-1 text-xs font-semibold text-ink" data-testid={`cue-status-${cue.cueCode}`}>
                        {cue.reviewStatus === "acknowledged" ? "Confirmed by therapist" : cue.reviewStatus === "dismissed" ? "Dismissed by therapist" : "Not yet reviewed"}
                      </span>
                    )}
                    {transcriptHref && (cue.evidence ?? []).length > 0 ? (
                      <a href={transcriptHref} className="text-sm font-semibold text-brand underline">Open transcript</a>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          ) : null}
          {mlDecisionSupport.patternEvidence ? (
            <div className="rounded-panel border border-line bg-surface p-4">
              <p className="font-semibold text-ink">{patternEvidenceTitle(mlDecisionSupport.patternEvidence.status)}</p>
              <EvidenceAvailabilityView availability={mlDecisionSupport.patternEvidence.availability} />
            </div>
          ) : null}
          {(mlDecisionSupport.profileEvidence ?? []).map((profile) => {
            const visibleFeatures = showEvidenceDetails
              ? profile.associatedFeatures
              : profile.associatedFeatures.slice(0, Math.max(0, 3 - initialEvidenceCueCount));
            initialEvidenceCueCount += visibleFeatures.length;
            return (
              <article key={profile.profileCode} className="rounded-panel border border-line bg-surface p-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="font-semibold text-ink">{profile.profileCode} profile</p>
                    <p className="text-xs text-ink-muted">Presentation group: {profile.presentationGroup}</p>
                  </div>
                  <span className="rounded-full bg-surface-muted px-3 py-1 text-xs font-semibold text-ink">
                    {profileStatusTitle(profile.status)}
                  </span>
                </div>
                <p className="mt-2 text-xs text-ink-muted">
                  Reference support: {profile.participantCount} participants · {profile.corpusCount} corpora
                </p>
                <EvidenceAvailabilityView availability={profile.availability} />
                {profile.availability.state === "insufficient_reference_data" ? (
                  <p className="mt-3 rounded-card bg-[color:var(--color-warning-bg)] px-3 py-2 text-sm font-medium text-[color:var(--color-warning-text)]">
                    Reference comparison unavailable
                  </p>
                ) : null}
                {visibleFeatures.map((feature) => (
                  <div key={feature.featureName} className="mt-3 rounded-panel border border-line bg-surface-muted p-3" data-testid={showEvidenceDetails ? "evidence-detail" : "evidence-cue"}>
                    <p className="text-sm font-semibold text-ink">{featureLabel(feature.featureName)}</p>
                    <p className="mt-1 text-sm text-ink-muted">
                      Observed {String(feature.observedValue)} · {positionTitle(feature.position)}
                    </p>
                    {showEvidenceDetails ? (
                      <p className="mt-1 text-xs text-ink-muted">
                        Reference distribution Q1 {String(feature.q1)} · median {String(feature.median)} · Q3 {String(feature.q3)}
                      </p>
                    ) : null}
                    <p className="mt-1 text-xs text-ink-muted">{feature.caveat}</p>
                  </div>
                ))}
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="rounded-card border border-line bg-surface-muted px-3 py-2 text-sm font-semibold text-brand-strong"
                    onClick={() => onProfileEvidenceReview(profile.profileCode, "reviewed")}
                    disabled={busy}
                  >
                    Reviewed
                  </button>
                  <button
                    type="button"
                    className="rounded-card border border-line bg-surface-muted px-3 py-2 text-sm font-semibold text-ink"
                    onClick={() => {
                      setDisagreementProfile(profile.profileCode);
                      setDisagreementNote(profile.reviewState.therapistNote);
                    }}
                    disabled={busy}
                  >
                    Record disagreement
                  </button>
                </div>
                {disagreementProfile === profile.profileCode ? (
                  <div className="mt-3 rounded-panel border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] p-3">
                    <p className="text-xs text-[color:var(--color-warning-text)]">
                      This records clinical disagreement and preserves the original provider output.
                    </p>
                    <textarea
                      aria-label={`Disagreement note for ${profile.profileCode}`}
                      className="mt-2 min-h-24 w-full rounded-panel border border-line bg-surface p-3 text-sm"
                      value={disagreementNote}
                      onChange={(event) => setDisagreementNote(event.target.value)}
                    />
                    <div className="mt-2 flex gap-2">
                      <button
                        type="button"
                        className="rounded-card bg-brand-strong px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
                        disabled={busy || !disagreementNote.trim()}
                        onClick={() => {
                          onProfileEvidenceReview(profile.profileCode, "disagreement", disagreementNote.trim());
                          setDisagreementProfile(undefined);
                          setDisagreementNote("");
                        }}
                      >
                        Save disagreement
                      </button>
                      <button
                        type="button"
                        className="rounded-card px-3 py-2 text-sm font-semibold text-ink"
                        onClick={() => {
                          setDisagreementProfile(undefined);
                          setDisagreementNote("");
                        }}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : null}
              </article>
            );
          })}
          {(mlDecisionSupport.profileEvidence ?? []).some((profile) => profile.associatedFeatures.length > 0) ? (
            <button
              type="button"
              className="text-sm font-semibold text-brand-strong underline"
              onClick={() => setShowEvidenceDetails((value) => !value)}
            >
              {showEvidenceDetails ? "Hide supporting evidence" : "View supporting evidence"}
            </button>
          ) : null}
        </div>
      ) : null}
      </div>
    </details>
  );
}
