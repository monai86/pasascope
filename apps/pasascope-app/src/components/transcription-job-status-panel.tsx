"use client";
import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Clock, Loader2, RefreshCw, XCircle } from "lucide-react";

import { audioCaptureMessages } from "@/components/audio-capture.messages";
import { useMessages } from "@/i18n/locale-provider";
import { useSafetyCopy } from "@/lib/safety-copy";

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

const CFG: Record<TranscriptionJobDisplayStatus, { icon: React.ReactNode; color: string }> = {
  queued:       { icon: <Clock size={18} />, color: "text-ink-muted" },
  processing:   { icon: <Loader2 size={18} className="animate-spin motion-reduce:animate-none" />, color: "text-brand-strong" },
  completed:    { icon: <CheckCircle2 size={18} />, color: "text-[color:var(--color-success-text)]" },
  needs_review: { icon: <CheckCircle2 size={18} />, color: "text-[color:var(--color-success-text)]" },
  failed:       { icon: <XCircle size={18} />, color: "text-[color:var(--color-danger-text)]" },
  cancelled:    { icon: <XCircle size={18} />, color: "text-ink-muted" },
  unavailable:  { icon: <AlertTriangle size={18} />, color: "text-[color:var(--color-warning-text)]" },
};

/** Seconds this panel has shown the job as still running; it restarts if the page reloads. */
function useWaitSeconds(running: boolean) {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(() => setSeconds((value) => value + 1), 1000);
    return () => window.clearInterval(timer);
  }, [running]);
  return seconds;
}

function clock(seconds: number) {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

export function TranscriptionJobStatusPanel({
  status, message, requestedProvider, actualProvider, fallbackReason,
  onOpenTranscript, onRetry, onUsePaste,
}: Props) {
  const t = useMessages(audioCaptureMessages).job;
  const safety = useSafetyCopy();
  const known = status in CFG ? status : "queued";
  const cfg = CFG[known];
  const label = known === "needs_review" ? safety.DRAFT_TRANSCRIPT_READY_LABEL : t.status[known];
  const isRunning = known === "queued" || known === "processing";
  const waitSeconds = useWaitSeconds(isRunning);
  const isSuccess = status === "completed" || status === "needs_review";
  const isError = status === "failed" || status === "unavailable";

  return (
    <div role="region" aria-label={t.regionLabel} aria-live="polite"
      className="rounded-panel border border-line bg-surface p-5 space-y-4">
      <div className={`flex items-center gap-2 font-semibold ${cfg.color}`}>
        {cfg.icon}<span>{label}</span>
        {isRunning ? <span aria-hidden="true" className="ml-auto text-sm font-medium tabular-nums text-ink-muted">{t.waiting(clock(waitSeconds))}</span> : null}
      </div>
      <p className="text-sm text-ink">{message}</p>
      {fallbackReason && (
        <p className="rounded-lg border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] px-4 py-2 text-sm text-[color:var(--color-warning-text)]">
          {t.fallback(fallbackReason)}
        </p>
      )}
      {actualProvider && requestedProvider && actualProvider !== requestedProvider && (
        <p className="text-xs text-ink-muted">{t.requestedUsed(requestedProvider, actualProvider)}</p>
      )}
      {actualProvider && (
        <p className="text-xs text-ink-muted">{t.transcribedBy(t.providers[actualProvider] ?? actualProvider)}</p>
      )}
      {isSuccess && (
        <div className="rounded-card border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] p-3 text-sm text-[color:var(--color-warning-text)]">
          <strong>{t.draftLabel}</strong> {t.draftNote(safety.THERAPIST_REVIEW_REQUIRED_CLAUSE)}
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        {isSuccess && onOpenTranscript && (
          <button type="button" id="btn-open-draft-transcript" onClick={onOpenTranscript}
            className="inline-flex items-center gap-2 rounded-card bg-brand px-5 py-2.5 text-sm font-semibold text-white">
            {t.review}
          </button>
        )}
        {isError && onRetry && (
          <button type="button" onClick={onRetry}
            className="inline-flex items-center gap-2 rounded-card border border-line-strong bg-surface px-4 py-2 text-sm font-semibold text-ink">
            <RefreshCw size={15} aria-hidden="true" /> {t.retry}
          </button>
        )}
        {isError && onUsePaste && (
          <button type="button" onClick={onUsePaste}
            className="inline-flex items-center gap-2 rounded-card border border-brand px-4 py-2 text-sm font-semibold text-brand">
            {t.usePaste}
          </button>
        )}
      </div>
    </div>
  );
}
