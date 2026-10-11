"use client";

import React, { useState, useEffect } from "react";
import { Gauge, Radio, Clock, ShieldCheck } from "lucide-react";
import { WaveformMinimap } from "./waveform-minimap";
import { WaveformDetailCanvas, type WaveformSegment } from "./waveform-detail-canvas";
import { SPEAKER_COLOURS, SPEAKER_ROLE_LABELS, type SpeakerRole } from "@/design-system/dataviz";

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
  // Zoom window duration (e.g. 20 seconds = 20,000 ms)
  const DETAIL_WINDOW_MS = 20000;

  // Viewport window state
  const [viewportStartMs, setViewportStartMs] = useState(0);
  const [viewportEndMs, setViewportEndMs] = useState(Math.min(durationMs || DETAIL_WINDOW_MS, DETAIL_WINDOW_MS));

  // Automatically keep viewport centered around currentTimeMs when playing outside window
  useEffect(() => {
    if (currentTimeMs < viewportStartMs || currentTimeMs > viewportEndMs) {
      const half = DETAIL_WINDOW_MS / 2;
      let start = Math.max(0, currentTimeMs - half);
      let end = start + DETAIL_WINDOW_MS;
      if (durationMs > 0 && end > durationMs) {
        end = durationMs;
        start = Math.max(0, durationMs - DETAIL_WINDOW_MS);
      }
      setViewportStartMs(start);
      setViewportEndMs(end);
    }
  }, [currentTimeMs, viewportStartMs, viewportEndMs, durationMs]);

  const handleViewportChange = (newStart: number, newEnd: number) => {
    setViewportStartMs(newStart);
    setViewportEndMs(newEnd);
  };

  return (
    <div
      className={`flex flex-col gap-2 rounded-card border border-navy-line bg-navy p-3 text-on-navy shadow-lift ${className}`}
      data-testid="dual-view-waveform"
    >
      {/* Legend and measured indicators */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-navy-line pb-2 text-xs">
        {/* Speaker legend: the dot carries the colour, the label stays in text ink. */}
        <ul className="flex flex-wrap items-center gap-3" aria-label="Speaker colours">
          {(Object.keys(SPEAKER_ROLE_LABELS) as SpeakerRole[]).map((role) => (
            <li key={role} className="flex items-center gap-1.5 font-medium text-on-navy-muted">
              <span aria-hidden="true" className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: SPEAKER_COLOURS.navy[role] }} />
              {SPEAKER_ROLE_LABELS[role]}
            </li>
          ))}
        </ul>

        <div className="flex items-center gap-3 font-mono">
          {typeof snrDb === "number" && (
            <div
              className="flex items-center gap-1 rounded-full bg-navy-raised px-2 py-0.5 text-on-navy-muted"
              title="Signal-to-Noise Ratio (Clean audio > 15 dB)"
            >
              <Radio size={12} aria-hidden="true" className="text-tint" />
              <span>SNR: {snrDb.toFixed(1)} dB</span>
            </div>
          )}

          {typeof diarizationConfidence === "number" && (
            <div
              className="flex items-center gap-1 rounded-full bg-navy-raised px-2 py-0.5 text-on-navy-muted"
              title="Diarization Alignment Confidence"
            >
              <ShieldCheck size={12} aria-hidden="true" className="text-tint" />
              <span>Diarization: {diarizationConfidence.toFixed(1)}%</span>
            </div>
          )}

          {typeof responseLatencyMs === "number" && (
            <div
              className="flex items-center gap-1 rounded-full bg-navy-raised px-2 py-0.5 text-on-navy-muted"
              title="Clinician-to-Child Turn-taking Latency"
            >
              <Clock size={12} aria-hidden="true" className="text-tint" />
              <span>Latency: {Math.round(responseLatencyMs)} ms</span>
            </div>
          )}
        </div>
      </div>

      {/* Mini-map Full Overview */}
      <div className="relative">
        <WaveformMinimap
          durationMs={durationMs}
          currentTimeMs={currentTimeMs}
          viewportStartMs={viewportStartMs}
          viewportEndMs={viewportEndMs}
          peaks={peaks}
          onViewportChange={handleViewportChange}
          onSeek={onSeek}
        />
      </div>

      {/* High-Resolution Detail Canvas */}
      <div className="relative">
        <WaveformDetailCanvas
          currentTimeMs={currentTimeMs}
          viewportStartMs={viewportStartMs}
          viewportEndMs={viewportEndMs}
          segments={segments}
          peaks={peaks}
          onSeek={onSeek}
          onSegmentBoundaryChange={onSegmentBoundaryChange}
        />
      </div>
    </div>
  );
}
