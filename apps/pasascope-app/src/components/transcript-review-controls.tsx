"use client";

import { CheckCircle2, Download, FileCheck2, MessageSquarePlus, Save, ShieldCheck } from "lucide-react";

import { speakerBulkMessages } from "@/components/transcript-speaker-bulk.messages";
import { useMessages } from "@/i18n/locale-provider";
import { useAppMode } from "@/lib/app-mode";
import { useGateReason } from "@/lib/gate-reason";
import { useSafetyCopy } from "@/lib/safety-copy";
import type { PersistenceStatus, TranscriptQaStatus } from "@/lib/workflow";
import { attestTranscriptBlockedReason, exportTranscriptBlockedReason } from "@/lib/workflow-gates";

const QA_TONE: Record<TranscriptQaStatus, string> = {
  not_run: "bg-surface-muted text-ink-muted",
  pass: "bg-[color:var(--color-success-bg)] text-[color:var(--color-success-text)]",
  warning: "bg-[color:var(--color-warning-bg)] text-[color:var(--color-warning-text)]",
  fail: "bg-[color:var(--color-danger-bg)] text-[color:var(--color-danger-text)]",
};

/** The result of the last QA run, folded until wanted unless it found something. */
export function TranscriptQaDetails({
  qaStatus,
  qaIssues,
  qaBlockedReason,
  open,
  onToggle,
}: {
  qaStatus: TranscriptQaStatus;
  qaIssues: string[];
  qaBlockedReason?: string;
  open: boolean;
  onToggle: (open: boolean) => void;
}) {
  const qa = useMessages(speakerBulkMessages).editor.qa;
  const safety = useSafetyCopy();
  return (
    <details
      className="group rounded-panel border border-line bg-surface"
      data-testid="mobile-transcript-qa-details"
      open={open}
      onToggle={(event) => onToggle(event.currentTarget.open)}
    >
      <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-3 px-4 py-2 text-sm font-semibold text-ink [&::-webkit-details-marker]:hidden">
        <span className="flex items-center gap-2">
          <FileCheck2 size={17} aria-hidden="true" className="text-brand" />
          {qa.title}
        </span>
        <span className="flex items-center gap-2 text-xs font-medium text-ink-muted">
          {qaIssues.length > 0 ? <span>{qa.items(qaIssues.length)}</span> : null}
          <span className={`rounded-full px-2.5 py-0.5 font-semibold ${QA_TONE[qaStatus]}`}>{qa.status[qaStatus]}</span>
        </span>
      </summary>
      <div className="border-t border-line px-4 py-3 text-sm" data-testid="transcript-qa-panel">
        {qaIssues.length > 0 ? (
          <ul className="list-disc space-y-1 pl-5 text-[color:var(--color-warning-text)]">
            {qaIssues.map((issue) => <li key={issue}>{issue}</li>)}
          </ul>
        ) : (
          <p className="text-ink-muted">{qaStatus === "not_run" ? qa.notRun : qa.none}</p>
        )}
        {qaBlockedReason ? (
          <p id="transcript-qa-blocked-reason" role="status" className="mt-2 font-medium text-[color:var(--color-warning-text)]">
            {qaBlockedReason}
          </p>
        ) : null}
        <p className="mt-2 text-xs text-ink-muted">{safety.QA_INTERPRETATION_NOTE}</p>
      </div>
    </details>
  );
}

/** What is left once the words and speakers are right: a note, attestation where the workspace asks for it, and export. */
export function TranscriptDoneActions({
  busy,
  linesCount,
  qaStatus,
  attested,
  onAddNote,
  onAttest,
  onExport,
}: {
  busy: boolean;
  linesCount: number;
  qaStatus: TranscriptQaStatus;
  attested: boolean;
  onAddNote: () => void;
  onAttest: () => void;
  onExport: () => void;
}) {
  const { openGates } = useAppMode();
  const done = useMessages(speakerBulkMessages).editor.done;
  const gate = useGateReason();
  const attestBlockedReason = gate(attestTranscriptBlockedReason({ busy, attested, linesCount, qaStatus }));
  const exportBlockedReason = gate(exportTranscriptBlockedReason({ busy, linesCount }));
  const quiet = "inline-flex min-h-11 items-center gap-2 rounded-full border border-line bg-surface px-4 text-sm font-semibold text-ink transition hover:bg-surface-soft disabled:opacity-50 motion-reduce:transition-none";

  return (
    <section
      aria-labelledby="transcript-done-title"
      className="rounded-panel border border-line bg-surface px-4 py-4"
      data-testid="mobile-transcript-secondary-actions"
    >
      <h3 id="transcript-done-title" className="font-semibold text-ink">{done.title}</h3>
      <p className="mt-1 max-w-[62ch] text-sm text-ink-muted">{done.body}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {openGates ? null : (
          <button
            type="button"
            onClick={onAttest}
            disabled={Boolean(attestBlockedReason) || attested}
            className="inline-flex min-h-11 items-center gap-2 rounded-full bg-action px-4 text-sm font-semibold text-white transition hover:bg-action-hover disabled:bg-surface-muted disabled:text-ink-muted motion-reduce:transition-none"
            data-testid="attest-transcript-button"
            aria-describedby={attestBlockedReason ? "transcript-attest-reason" : undefined}
          >
            {attested ? <CheckCircle2 size={17} aria-hidden="true" /> : <ShieldCheck size={17} aria-hidden="true" />}
            {attested ? done.attested : done.attest}
          </button>
        )}
        <button type="button" onClick={onAddNote} disabled={busy} className={quiet}>
          <MessageSquarePlus size={16} aria-hidden="true" />
          {done.addNote}
        </button>
        <button
          type="button"
          onClick={onExport}
          disabled={Boolean(exportBlockedReason)}
          className={quiet}
          aria-describedby={exportBlockedReason ? "transcript-export-reason" : undefined}
        >
          <Download size={16} aria-hidden="true" />
          {done.export}
        </button>
      </div>
      {attestBlockedReason && !openGates && !attested ? (
        <p id="transcript-attest-reason" role="status" className="mt-3 text-sm font-medium text-[color:var(--color-warning-text)]">
          {attestBlockedReason}
        </p>
      ) : null}
      {exportBlockedReason ? (
        <p id="transcript-export-reason" role="status" className="mt-2 text-sm font-medium text-[color:var(--color-warning-text)]">
          {exportBlockedReason}
        </p>
      ) : null}
    </section>
  );
}

/**
 * Save and QA, pinned to the bottom of the page while the lines are edited,
 * with the save state beside them so an unsaved change is never a surprise.
 */
export function TranscriptSaveBar({
  busy,
  saveStatus,
  qaBlockedReason,
  onSaveDraft,
  onRunQa,
}: {
  busy: boolean;
  saveStatus: PersistenceStatus;
  qaBlockedReason?: string;
  onSaveDraft: () => void;
  onRunQa: () => void;
}) {
  const editor = useMessages(speakerBulkMessages).editor;
  const saved = saveStatus === "saved";
  return (
    <div className="sticky bottom-2 z-20 flex flex-wrap items-center justify-between gap-x-3 gap-y-1.5 rounded-panel border border-line bg-surface px-3 py-2 sm:pl-4 sm:pr-2 shadow-lift max-sm:pb-[calc(0.5rem+env(safe-area-inset-bottom,0px))]">
      <p className="flex min-w-0 basis-full items-center gap-2 px-0.5 text-sm font-medium text-ink-muted sm:basis-auto" role="status" aria-live="polite" aria-label={editor.save.label}>
        <span
          aria-hidden="true"
          className={`h-2 w-2 shrink-0 rounded-full ${saved ? "bg-brand" : saveStatus === "failed" ? "bg-[color:var(--color-danger-text)]" : "bg-[color:var(--color-warning-text)]"}`}
        />
        <span className="truncate">{editor.save.status[saveStatus]}</span>
      </p>
      <div className="flex flex-1 justify-end gap-2 sm:flex-none" data-testid="mobile-transcript-primary-actions">
        <button
          type="button"
          onClick={onSaveDraft}
          disabled={busy}
          className="inline-flex min-h-11 flex-1 items-center justify-center gap-2 rounded-full border border-action-quiet-border bg-surface px-4 text-sm font-semibold text-action-quiet-text transition hover:bg-action-quiet-hover disabled:opacity-50 motion-reduce:transition-none sm:flex-none"
          data-testid="save-transcript-draft-button"
        >
          <Save size={16} aria-hidden="true" />
          {editor.saveDraft}
        </button>
        <button
          type="button"
          onClick={onRunQa}
          disabled={busy || Boolean(qaBlockedReason)}
          title={qaBlockedReason}
          aria-describedby={qaBlockedReason ? "transcript-qa-blocked-reason" : undefined}
          className="inline-flex min-h-11 flex-1 items-center justify-center gap-2 rounded-full bg-action px-4 text-sm font-semibold text-white transition hover:bg-action-hover disabled:bg-surface-muted disabled:text-ink-muted motion-reduce:transition-none sm:flex-none"
          data-testid="run-transcript-qa-button"
        >
          <FileCheck2 size={16} aria-hidden="true" />
          {editor.runQa}
        </button>
      </div>
    </div>
  );
}
