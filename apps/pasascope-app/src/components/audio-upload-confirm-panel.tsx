"use client";
import { AlertTriangle, Upload, X } from "lucide-react";

import { audioCaptureMessages } from "@/components/audio-capture.messages";
import { useMessages } from "@/i18n/locale-provider";
import { useSafetyCopy } from "@/lib/safety-copy";

type AudioUploadConfirmPanelProps = {
  blob: Blob;
  durationSeconds: number;
  onUpload: () => void;
  onCancel: () => void;
  backendAvailable: boolean;
  uploading?: boolean;
};

export function AudioUploadConfirmPanel({
  blob, durationSeconds, onUpload, onCancel, backendAvailable, uploading = false,
}: AudioUploadConfirmPanelProps) {
  const t = useMessages(audioCaptureMessages).upload;
  const safety = useSafetyCopy();
  const mins = Math.floor(durationSeconds / 60);
  const secs = durationSeconds % 60;
  const duration = `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  const sizeMb = (blob.size / 1024 / 1024).toFixed(1);

  return (
    <div role="region" aria-label={t.regionLabel}
      className="rounded-panel border border-[color:var(--color-attention-border)] bg-[color:var(--color-warning-bg)] p-5 space-y-4">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 shrink-0 text-[color:var(--color-warning-text)]" size={20} aria-hidden="true" />
        <div>
          <p className="font-semibold text-[color:var(--color-warning-text)]">{t.title}</p>
          <p className="mt-1 text-sm text-[color:var(--color-warning-text)]">{t.recording(duration, sizeMb)}</p>
        </div>
      </div>
      <div className="rounded-card border border-[color:var(--color-attention-border)] bg-surface p-4 text-sm text-[color:var(--color-warning-text)] space-y-2">
        <p>
          <strong>{t.privacyLabel}</strong> {t.privacyBody}
        </p>
        <p>{t.notStored}</p>
        <p className="font-semibold">
          {safety.EXPERIMENTAL_ASR_CAUTION}
        </p>
      </div>
      {!backendAvailable && (
        <p className="rounded-card border border-[color:var(--color-danger-border)] bg-[color:var(--color-danger-bg)] px-4 py-3 text-sm font-semibold text-[color:var(--color-danger-text)]" role="alert">
          {t.backendUnavailable}
        </p>
      )}
      <div className="flex flex-wrap gap-3">
        <button type="button" id="btn-upload-for-transcription"
          onClick={onUpload} disabled={!backendAvailable || uploading}
          aria-busy={uploading}
          className="inline-flex items-center gap-2 rounded-card bg-brand px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-40 disabled:cursor-not-allowed">
          <Upload size={16} aria-hidden="true" />
          {uploading ? t.uploading : t.upload}
        </button>
        <button type="button" onClick={onCancel} disabled={uploading}
          className="inline-flex items-center gap-2 rounded-card border border-line-strong bg-surface px-5 py-2.5 text-sm font-semibold text-ink disabled:opacity-40">
          <X size={16} aria-hidden="true" /> {t.cancel}
        </button>
      </div>
    </div>
  );
}
