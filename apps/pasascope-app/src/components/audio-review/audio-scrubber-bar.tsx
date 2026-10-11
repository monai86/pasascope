"use client";

import React from "react";
import { Play, Pause, Repeat, Volume2 } from "lucide-react";

export interface AudioScrubberBarProps {
  isPlaying: boolean;
  currentTimeMs: number;
  durationMs: number;
  speed: number;
  isLooping: boolean;
  onPlayPause: () => void;
  onSpeedChange: (speed: number) => void;
  onToggleLoop: () => void;
  onSeek?: (timeMs: number) => void;
}

export function formatTimecode(ms: number): string {
  const totalSeconds = Math.max(0, ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = Math.floor(totalSeconds % 60);
  const millis = Math.floor(ms % 1000);
  const pad = (n: number, z = 2) => String(n).padStart(z, "0");
  return `${pad(minutes)}:${pad(seconds)}.${pad(millis, 3)}`;
}

export function AudioScrubberBar({
  isPlaying,
  currentTimeMs,
  durationMs,
  speed,
  isLooping,
  onPlayPause,
  onSpeedChange,
  onToggleLoop,
  onSeek,
}: AudioScrubberBarProps) {
  const speeds = [0.75, 1.0, 1.25];
  const progressPercent = durationMs > 0 ? Math.min(100, Math.max(0, (currentTimeMs / durationMs) * 100)) : 0;

  const handleScrubberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (onSeek) {
      const targetMs = (Number(e.target.value) / 100) * durationMs;
      onSeek(targetMs);
    }
  };

  return (
    <div
      className="flex flex-wrap items-center justify-between gap-3 rounded-card border border-navy-line bg-navy px-4 py-2.5 text-on-navy shadow-soft"
      data-testid="audio-scrubber-bar"
    >
      {/* Play/Pause & Times */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onPlayPause}
          aria-label={isPlaying ? "Pause" : "Play"}
          className="flex h-11 w-11 items-center justify-center rounded-full bg-surface text-brand-strong transition hover:bg-brand-soft focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-sky)]"
        >
          {isPlaying ? <Pause size={18} /> : <Play size={18} className="translate-x-0.5" />}
        </button>

        <div className="font-mono text-sm tracking-tight text-on-navy-muted">
          <span className="font-semibold text-white">{formatTimecode(currentTimeMs)}</span>
          <span className="text-on-navy-subtle"> / </span>
          <span className="text-on-navy-subtle">{formatTimecode(durationMs)}</span>
        </div>
      </div>

      {/* Scrubber slider */}
      <div className="flex min-w-[200px] flex-1 items-center px-2">
        <input
          type="range"
          min="0"
          max="100"
          step="0.01"
          value={progressPercent}
          onChange={handleScrubberChange}
          aria-label="Audio scrubber"
          className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-navy-line accent-[color:var(--color-sky)] transition hover:bg-navy-raised focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--color-sky)]"
        />
      </div>

      {/* Speed and loop controls */}
      <div className="flex items-center gap-2">
        <div className="flex rounded-full bg-navy-raised p-0.5" role="group" aria-label="Playback speed">
          {speeds.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => onSpeedChange(s)}
              aria-pressed={speed === s}
              className={`min-h-9 rounded-full px-2.5 py-1 text-xs font-semibold transition ${
                speed === s
                  ? "bg-surface text-brand-strong"
                  : "text-on-navy-muted hover:text-on-navy"
              }`}
            >
              {s.toFixed(2).replace(/\.?0+$/, "")}x
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={onToggleLoop}
          aria-label="Loop"
          aria-pressed={isLooping}
          className={`flex min-h-9 items-center gap-1 rounded-full px-3 py-1 text-xs font-medium transition ${
            isLooping
              ? "bg-surface text-brand-strong"
              : "bg-navy-raised text-on-navy-muted hover:bg-navy-line hover:text-on-navy"
          }`}
        >
          <Repeat size={14} />
          <span>Loop</span>
        </button>
      </div>
    </div>
  );
}
