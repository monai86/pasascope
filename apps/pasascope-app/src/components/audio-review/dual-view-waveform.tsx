"use client";

import React, { useEffect, useRef, useState } from "react";
import { Clock, Radio, ShieldCheck } from "lucide-react";

import { audioReviewMessages } from "@/components/audio-review/audio-review.messages";
import { useElementSize } from "@/components/audio-review/use-element-size";
import { WaveformDetailCanvas, type WaveformSegment } from "@/components/audio-review/waveform-detail-canvas";
import { WaveformMinimap } from "@/components/audio-review/waveform-minimap";
import { SPEAKER_COLOURS, type SpeakerRole } from "@/design-system/dataviz";
import { useMessages } from "@/i18n/locale-provider";

export interface DualViewWaveformProps {
  currentTimeMs: number;
  durationMs: number;
  segments: WaveformSegment[];
  peaks?: Int8Array | null;
  snrDb?: number;
  diarizationConfidence?: number;
  responseLatencyMs?: number;
  onSeek?: (timeMs: number) => void;
  onSegmentBoundaryChange?: (segmentId: string, startMs: number, endMs: number) => void;
  className?: string;
}

const SPEAKER_ROLES: SpeakerRole[] = ["child", "clinician", "other"];

/** How much of the recording the close-up shows: about 20 ms a pixel, 8 to 20 seconds. */
function closeUpWindowMs(widthPx: number): number {
  if (widthPx <= 0) return 20_000;
  return Math.min(20_000, Math.max(8_000, Math.round((widthPx * 20) / 1000) * 1000));
}

/**
 * The recording drawn twice in one panel: the whole file as an overview, and
 * a close-up that follows the playhead. The close-up spans fewer seconds on a
 * narrow screen, so a line is still wide enough to see and to grab.
 */
export function DualViewWaveform({
  currentTimeMs,
  durationMs,
  segments,
  peaks,
  snrDb,
  diarizationConfidence,
  responseLatencyMs,
  onSeek,
  onSegmentBoundaryChange,
  className = "",
}: DualViewWaveformProps) {
  const t = useMessages(audioReviewMessages).waveform;
  const panelRef = useRef<HTMLDivElement | null>(null);
  const { width } = useElementSize(panelRef);
  const windowMs = closeUpWindowMs(width);

  const [viewportStartMs, setViewportStartMs] = useState(0);
  const viewportEndMs = Math.min(durationMs > 0 ? durationMs : windowMs, viewportStartMs + windowMs);

  // Keep the playhead inside the close-up while it plays.
  useEffect(() => {
    if (currentTimeMs >= viewportStartMs && currentTimeMs <= viewportEndMs) return;
    let start = Math.max(0, currentTimeMs - windowMs / 2);
    if (durationMs > 0 && start + windowMs > durationMs) start = Math.max(0, durationMs - windowMs);
    setViewportStartMs(start);
  }, [currentTimeMs, viewportStartMs, viewportEndMs, durationMs, windowMs]);

  const measures = [
    typeof snrDb === "number" ? { icon: Radio, text: `SNR: ${snrDb.toFixed(1)} dB` } : null,
    typeof diarizationConfidence === "number" ? { icon: ShieldCheck, text: `Diarization: ${diarizationConfidence.toFixed(1)}%` } : null,
    typeof responseLatencyMs === "number" ? { icon: Clock, text: `Latency: ${Math.round(responseLatencyMs)} ms` } : null,
  ].filter((measure) => measure !== null);

  return (
    <div
      ref={panelRef}
      className={`grid gap-2.5 rounded-panel border border-navy-line bg-navy p-3 text-on-navy sm:p-4 ${className}`}
      data-testid="dual-view-waveform"
      role="group"
      aria-label={t.label}
    >
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1.5 text-xs">
        {/* The dot carries the colour; the name stays in text ink. */}
        <ul className="flex flex-wrap items-center gap-x-4 gap-y-1">
          {SPEAKER_ROLES.map((role) => (
            <li key={role} className="flex items-center gap-1.5 font-medium text-on-navy-muted">
              <span aria-hidden="true" className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: SPEAKER_COLOURS.navy[role] }} />
              {t.speakers[role]}
            </li>
          ))}
        </ul>
        {measures.length > 0 ? (
          <ul className="flex flex-wrap items-center gap-2 font-mono text-on-navy-muted">
            {measures.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-1 rounded-full bg-navy-raised px-2 py-0.5">
                <Icon size={12} aria-hidden="true" className="text-tint" />
                {text}
              </li>
            ))}
          </ul>
        ) : null}
      </div>

      <WaveformMinimap
        durationMs={durationMs}
        currentTimeMs={currentTimeMs}
        viewportStartMs={viewportStartMs}
        viewportEndMs={viewportEndMs}
        peaks={peaks}
        label={t.overview}
        onViewportChange={(start) => setViewportStartMs(start)}
        onSeek={onSeek}
      />

      <WaveformDetailCanvas
        currentTimeMs={currentTimeMs}
        viewportStartMs={viewportStartMs}
        viewportEndMs={viewportEndMs}
        segments={segments}
        peaks={peaks}
        durationMs={durationMs}
        label={t.detail}
        onSeek={onSeek}
        onSegmentBoundaryChange={onSegmentBoundaryChange}
      />

      <p className="text-xs text-on-navy-subtle">{peaks === null ? t.noWaveform : t.hint}</p>
    </div>
  );
}
