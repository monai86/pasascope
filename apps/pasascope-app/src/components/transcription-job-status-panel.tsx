"use client";
import { AlertTriangle, CheckCircle2, Clock, Loader2, RefreshCw, XCircle } from "lucide-react";

import {
  DRAFT_TRANSCRIPT_READY_LABEL,
  THERAPIST_REVIEW_REQUIRED_CLAUSE,
} from "@/lib/clinical-safety-copy";

export type TranscriptionJobDisplayStatus =
  "queued" | "processing" | "completed" | "needs_review" | "failed" | "cancelled" | "unavailable";

type Props = {
  status: TranscriptionJobDisplayStatus;
  message: string;
  requestedProvider?: string;
  actualProvider?: string;
  fallbackReason?: string;
  onOpenTranscript?: () => void;
  onRetry?: () => void;
  onUsePaste?: () => void;
};

const CFG: Record<TranscriptionJobDisplayStatus, { icon: React.ReactNode; label: string; color: string }> = {
  queued:       { icon: <Clock size={18} />, label: "Queued", color: "text-ink-muted" },
  processing:   { icon: <Loader2 size={18} className="animate-spin" />, label: "Processing", color: "text-brand-strong" },
  completed:    { icon: <CheckCircle2 size={18} />, label: "Draft transcript ready", color: "text-[color:var(--color-success-text)]" },
  needs_review: { icon: <CheckCircle2 size={18} />, label: DRAFT_TRANSCRIPT_READY_LABEL, color: "text-[color:var(--color-success-text)]" },
  failed:       { icon: <XCircle size={18} />, label: "Transcription failed", color: "text-[color:var(--color-danger-text)]" },
  cancelled:    { icon: <XCircle size={18} />, label: "Cancelled", color: "text-ink-muted" },
  unavailable:  { icon: <AlertTriangle size={18} />, label: "Provider unavailable", color: "text-[color:var(--color-warning-text)]" },
};

const PROVIDER_LABELS: Record<string, string> = {
  local_whisper: "Whisper (on this server)",
  mock: "Synthetic demo text — not speech recognition",
  manual: "Manual entry",
};

export function TranscriptionJobStatusPanel({
  status, message, requestedProvider, actualProvider, fallbackReason,
  onOpenTranscript, onRetry, onUsePaste,
}: Props) {
  const cfg = CFG[status] ?? CFG.queued;
  const isSuccess = status === "completed" || status === "needs_review";
  const isError = status === "failed" || status === "unavailable";

  return (
    <div role="region" aria-label="Transcription job status" aria-live="polite"
      className="rounded-panel border border-line bg-surface p-5 space-y-4">
      <div className={`flex items-center gap-2 font-semibold ${cfg.color}`}>
        {cfg.icon}<span>{cfg.label}</span>
      </div>
      <p className="text-sm text-ink">{message}</p>
      {fallbackReason && (
        <p className="rounded-lg border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] px-4 py-2 text-sm text-[color:var(--color-warning-text)]">
          ⚠️ Fallback: {fallbackReason}
        </p>
      )}
      {actualProvider && requestedProvider && actualProvider !== requestedProvider && (
        <p className="text-xs text-ink-muted">Requested: {requestedProvider} · Used: {actualProvider}</p>
      )}
      {actualProvider && (
        <p className="text-xs text-ink-muted">Transcribed by: {PROVIDER_LABELS[actualProvider] ?? actualProvider}</p>
      )}
      {isSuccess && (
        <div className="rounded-card border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] p-3 text-sm text-[color:var(--color-warning-text)]">
          <strong>Draft ASR transcript.</strong> {THERAPIST_REVIEW_REQUIRED_CLAUSE} before feature extraction.
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        {isSuccess && onOpenTranscript && (
          <button type="button" id="btn-open-draft-transcript" onClick={onOpenTranscript}
            className="inline-flex items-center gap-2 rounded-card bg-brand px-5 py-2.5 text-sm font-semibold text-white">
            Review transcript
          </button>
        )}
        {isError && onRetry && (
          <button type="button" onClick={onRetry}
            className="inline-flex items-center gap-2 rounded-card border border-line-strong bg-surface px-4 py-2 text-sm font-semibold text-ink">
            <RefreshCw size={15} /> Retry
          </button>
        )}
        {isError && onUsePaste && (
          <button type="button" onClick={onUsePaste}
            className="inline-flex items-center gap-2 rounded-card border border-brand px-4 py-2 text-sm font-semibold text-brand">
            Use manual paste instead
          </button>
        )}
      </div>
    </div>
  );
}
