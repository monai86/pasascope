"use client";

import React from "react";
import { Pause, Play, Repeat } from "lucide-react";

import { audioReviewMessages } from "@/components/audio-review/audio-review.messages";
import { useMessages } from "@/i18n/locale-provider";

export interface AudioScrubberBarProps {
  isPlaying: boolean;
  currentTimeMs: number;
  durationMs: number;
  speed: number;
  isLooping?: boolean;
  onPlayPause: () => void;
  onSpeedChange: (speed: number) => void;
  /** Without it the player has no loop button. */
  onToggleLoop?: () => void;
  onSeek?: (timeMs: number) => void;
  className?: string;
}

export function formatTimecode(ms: number): string {
  const totalSeconds = Math.max(0, ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = Math.floor(totalSeconds % 60);
  const millis = Math.floor(ms % 1000);
  const pad = (n: number, z = 2) => String(n).padStart(z, "0");
  return `${pad(minutes)}:${pad(seconds)}.${pad(millis, 3)}`;
}

/** `m:ss.d`, a tenth of a second being as fine as anyone listens. */
export function formatClock(ms: number): string {
  const tenths = Math.floor(Math.max(0, ms) / 100);
  const minutes = Math.floor(tenths / 600);
  const seconds = Math.floor((tenths % 600) / 10);
  return `${minutes}:${String(seconds).padStart(2, "0")}.${tenths % 10}`;
}

const SPEEDS = [0.75, 1, 1.25] as const;

/**
 * Play, position, speed and loop for the recording. It stays at the top of
 * the page while the lines below are worked through, so it is one compact
 * band: the position slider shares the row from `sm` and takes a row of its
 * own on a phone, where it needs the full width to be dragged precisely.
 */
export function AudioScrubberBar({
  isPlaying,
  currentTimeMs,
  durationMs,
  speed,
  isLooping = false,
  onPlayPause,
  onSpeedChange,
  onToggleLoop,
  onSeek,
  className = "",
}: AudioScrubberBarProps) {
  const t = useMessages(audioReviewMessages).player;
  const progress = durationMs > 0 ? Math.min(100, Math.max(0, (currentTimeMs / durationMs) * 100)) : 0;

  return (
    <div
      className={`grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-x-3 gap-y-2 rounded-panel border border-navy-line bg-navy px-3 py-2.5 text-on-navy shadow-soft sm:flex sm:px-4 ${className}`}
      data-testid="audio-scrubber-bar"
    >
      <button
        type="button"
        onClick={onPlayPause}
        aria-label={isPlaying ? t.pause : t.play}
        className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-surface text-brand-strong transition hover:bg-brand-soft focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-sky)] motion-reduce:transition-none"
      >
        {isPlaying ? <Pause size={20} aria-hidden="true" /> : <Play size={20} aria-hidden="true" className="translate-x-0.5" />}
      </button>

      {/* Stacked on a phone so the speed and loop controls keep the same row. */}
      <p className="flex min-w-0 flex-col font-mono text-[13px] leading-tight tabular-nums text-on-navy-subtle sm:block sm:shrink-0 sm:text-sm">
        <span className="font-semibold text-white">{formatClock(currentTimeMs)}</span>
        <span>
          <span aria-hidden="true" className="hidden sm:inline"> / </span>
          <span className="sr-only"> of </span>
          {formatClock(durationMs)}
        </span>
      </p>

      <input
        type="range"
        min="0"
        max="100"
        step="0.01"
        value={progress}
        onChange={(event) => onSeek?.((Number(event.target.value) / 100) * durationMs)}
        aria-label={t.seek}
        aria-valuetext={`${formatClock(currentTimeMs)} / ${formatClock(durationMs)}`}
        style={{ "--progress": `${progress}%` } as React.CSSProperties}
        className="scrubber col-span-3 row-start-2 sm:min-w-0 sm:flex-1"
      />

      <div className="flex items-center gap-1.5 justify-self-end">
        <div className="flex rounded-full bg-navy-raised p-0.5" role="group" aria-label={t.speed}>
          {SPEEDS.map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => onSpeedChange(value)}
              aria-pressed={speed === value}
              className={`min-h-10 min-w-10 rounded-full px-2 font-mono text-xs font-semibold tabular-nums transition motion-reduce:transition-none ${
                speed === value ? "bg-surface text-brand-strong" : "text-on-navy-muted hover:text-on-navy"
              }`}
            >
              {value}x
            </button>
          ))}
        </div>
        {onToggleLoop ? (
          <button
            type="button"
            onClick={onToggleLoop}
            aria-pressed={isLooping}
            title={t.loopHint}
            className={`inline-flex min-h-11 min-w-11 items-center justify-center gap-1.5 rounded-full px-2.5 text-xs font-semibold transition motion-reduce:transition-none lg:px-3.5 ${
              isLooping ? "bg-surface text-brand-strong" : "bg-navy-raised text-on-navy-muted hover:text-on-navy"
            }`}
          >
            <Repeat size={15} aria-hidden="true" />
            <span className="sr-only lg:not-sr-only">{t.loop}</span>
          </button>
        ) : null}
      </div>
    </div>
  );
}
