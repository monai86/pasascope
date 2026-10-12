"use client";

import { useEffect, useState } from "react";
import {
  CheckCircle2,
  Download,
  FileCheck2,
  MessageSquarePlus,
  Save,
  ShieldCheck,
  SlidersHorizontal,
} from "lucide-react";

import { QaBadge } from "@/components/transcript-editor-support";
import { QA_INTERPRETATION_NOTE } from "@/lib/clinical-safety-copy";
import { attestTranscriptBlockedReason, exportTranscriptBlockedReason } from "@/lib/workflow-gates";
import type { PersistenceStatus, TranscriptQaStatus } from "@/lib/workflow";
import { useGateReason } from "@/lib/gate-reason";

type QaDetailsProps = {
  qaStatus: TranscriptQaStatus;
  qaIssues: string[];
  qaBlockedReason?: string;
  inspectorOpen: boolean;
  inspectorView: "audio" | "qa";
  open: boolean;
  onToggle: (open: boolean) => void;
};

export function TranscriptQaDetails({
  qaStatus,
  qaIssues,
  qaBlockedReason,
  inspectorOpen,
  inspectorView,
  open,
  onToggle,
}: QaDetailsProps) {
  return (
    <details
      className={`responsive-details mt-4 self-start rounded-panel border border-line bg-surface lg:col-start-2 lg:row-start-3 ${
        !inspectorOpen || inspectorView === "audio" ? "md:hidden" : "md:block"
      }`}
      data-testid="mobile-transcript-qa-details"
      open={open}
      onToggle={(event) => onToggle(event.currentTarget.open)}
    >
      <summary className="flex min-h-11 cursor-pointer items-center justify-between gap-3 px-4 py-3 text-sm font-semibold text-ink">
        <span>QA details</span>
        <span className="text-xs font-medium text-ink-muted">
          {qaStatus === "not_run" ? "Not run" : qaIssues.length > 0 ? `${qaIssues.length} item${qaIssues.length === 1 ? "" : "s"}` : "No issues"}
        </span>
      </summary>
      <div className="border-t border-line p-4 md:border-t-0" data-testid="transcript-qa-panel">
        <div className="flex items-center gap-2">
          <FileCheck2 size={18} aria-hidden="true" className="text-brand" />
          <h3 className="font-semibold text-ink">Transcript QA</h3>
          <QaBadge status={qaStatus} />
        </div>
        {qaIssues.length > 0 ? (
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-[color:var(--color-warning-text)]">
            {qaIssues.map((issue) => <li key={issue}>{issue}</li>)}
          </ul>
        ) : (
          <p className="mt-2 text-sm text-ink-muted">
            {qaStatus === "not_run" ? "Run QA after saving your edits." : "No QA issues were found."}
          </p>
        )}
        <p className="mt-3 text-xs text-ink-muted">{QA_INTERPRETATION_NOTE}</p>
        {qaBlockedReason ? (
          <p id="transcript-qa-blocked-reason" className="mt-3 rounded-card border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] px-3 py-2 text-sm font-semibold text-[color:var(--color-warning-text)]" role="status">
            {qaBlockedReason}
          </p>
        ) : null}
      </div>
    </details>
  );
}

type ReviewControlsProps = {
  busy: boolean;
  linesCount: number;
  selectedLineIndex: number;
  saveStatus: PersistenceStatus;
  qaBlockedReason?: string;
  qaStatus: TranscriptQaStatus;
  canAttest: boolean;
  attested: boolean;
  inspectorOpen: boolean;
  onSpeakerTools: () => void;
  onAddNote: () => void;
  onSaveDraft: () => void;
  onRunQa: () => void;
  onAttest: () => void;
  onExport: () => void;
};

export function TranscriptReviewControls({
  busy,
  linesCount,
  selectedLineIndex,
  saveStatus,
  qaBlockedReason,
  qaStatus,
  canAttest,
  attested,
  inspectorOpen,
  onSpeakerTools,
  onAddNote,
  onSaveDraft,
  onRunQa,
  onAttest,
  onExport,
}: ReviewControlsProps) {
  const gate = useGateReason();
  const attestBlockedReason = gate(attestTranscriptBlockedReason({
    busy,
    attested,
    linesCount,
    qaStatus,
  }));
  const exportBlockedReason = gate(exportTranscriptBlockedReason({ busy, linesCount }));
  const [secondaryOpen, setSecondaryOpen] = useState(canAttest || attested);

  useEffect(() => {
    if (canAttest || attested) setSecondaryOpen(true);
  }, [attested, canAttest]);

  return (
    <div className={`mt-5 grid gap-3 rounded-shell border border-line bg-surface p-3 max-md:pb-[calc(0.75rem+env(safe-area-inset-bottom,0px))] lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end ${inspectorOpen ? "lg:col-span-2 lg:row-start-5" : ""}`}>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center justify-between gap-2 px-1">
          <p className="text-xs font-semibold text-ink-muted" role="status" aria-live="polite" aria-label="Transcript save status">
            {saveStatus === "saving" ? "Saving transcript" : saveStatus === "saved" ? "Transcript saved" : saveStatus === "failed" ? "Failed to save transcript" : saveStatus === "unsaved" ? "Unsaved transcript changes" : "Transcript not saved"}
          </p>
          <p className="text-xs text-ink-muted">
            {selectedLineIndex >= 0 ? `Selected line ${selectedLineIndex + 1}` : "Select a line to use speaker tools and notes."}
          </p>
        </div>

        <details
          className="responsive-details mt-2"
          data-testid="mobile-transcript-secondary-actions"
          open={secondaryOpen}
          onToggle={(event) => setSecondaryOpen(event.currentTarget.open)}
        >
          <summary className="flex min-h-11 cursor-pointer items-center justify-between rounded-card border border-line px-3 text-sm font-semibold text-ink">
            <span>More review actions</span>
            <span aria-hidden="true">⌄</span>
          </summary>
          <div className="mt-2 flex flex-wrap gap-2 md:mt-0">
            <button
              type="button"
              onClick={onSpeakerTools}
              className="inline-flex min-h-11 items-center gap-2 rounded-card border border-line bg-surface px-3 py-2 text-sm font-semibold text-ink"
            >
              <SlidersHorizontal size={16} aria-hidden="true" />
              Speaker Tools
            </button>
            <button
              type="button"
              onClick={onAddNote}
              disabled={busy}
              className="inline-flex min-h-11 items-center gap-2 rounded-card border border-line bg-surface px-3 py-2 text-sm font-semibold text-ink disabled:opacity-50"
            >
              <MessageSquarePlus size={16} aria-hidden="true" />
              Add Note
            </button>
            <button
              type="button"
              onClick={onAttest}
              disabled={busy || !canAttest || attested}
              className="inline-flex min-h-11 items-center gap-2 rounded-card bg-ink px-3 py-2 text-sm font-semibold text-white disabled:bg-surface-muted"
              data-testid="attest-transcript-button"
              aria-describedby={attestBlockedReason ? "transcript-attest-reason" : undefined}
            >
              {attested ? <CheckCircle2 size={17} aria-hidden="true" /> : <ShieldCheck size={17} aria-hidden="true" />}
              {attested ? "Transcript attested" : "Attest transcript"}
            </button>
            <button
              type="button"
              onClick={onExport}
              disabled={busy || linesCount === 0}
              className="inline-flex min-h-11 items-center gap-2 rounded-card border border-line bg-surface px-3 py-2 text-sm font-semibold text-ink disabled:opacity-50"
              aria-describedby={exportBlockedReason ? "transcript-export-reason" : undefined}
            >
              <Download size={17} aria-hidden="true" />
              Export reviewed .cha
            </button>
          </div>
          {attestBlockedReason ? (
            <p
              id="transcript-attest-reason"
              role="status"
              className="mt-3 rounded-card border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] px-3 py-2 text-sm font-semibold text-[color:var(--color-warning-text)]"
            >
              {attestBlockedReason}
            </p>
          ) : null}
          {exportBlockedReason ? (
            <p
              id="transcript-export-reason"
              role="status"
              className="mt-3 rounded-card border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] px-3 py-2 text-sm font-semibold text-[color:var(--color-warning-text)]"
            >
              {exportBlockedReason}
            </p>
          ) : null}
        </details>
      </div>

      <div
        className="mobile-transcript-primary-actions grid grid-cols-2 gap-2"
        data-testid="mobile-transcript-primary-actions"
      >
        <button
          type="button"
          onClick={onSaveDraft}
          disabled={busy}
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-card border border-line bg-surface px-4 py-2 text-sm font-semibold text-ink disabled:opacity-50"
          data-testid="save-transcript-draft-button"
        >
          <Save size={17} aria-hidden="true" />
          Save draft
        </button>
        <button
          type="button"
          onClick={onRunQa}
          disabled={busy || Boolean(qaBlockedReason)}
          title={qaBlockedReason}
          aria-describedby={qaBlockedReason ? "transcript-qa-blocked-reason" : undefined}
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-card bg-brand px-4 py-2 text-sm font-semibold text-white disabled:bg-surface-muted disabled:text-ink-muted"
          data-testid="run-transcript-qa-button"
        >
          <FileCheck2 size={17} aria-hidden="true" />
          Run QA
        </button>
      </div>
    </div>
  );
}
